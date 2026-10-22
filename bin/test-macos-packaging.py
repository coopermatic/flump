#!/usr/bin/env python3
"""Test licensing guards everywhere and native signing on macOS without using AIR."""
import importlib.util
from pathlib import Path
import platform
import plistlib
import tempfile
import unittest

from macos_adhoc import run, sign, verify

spec = importlib.util.spec_from_file_location('licensing', Path(__file__).with_name('check-air-license.py'))
licensing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(licensing)


class LicenseTests(unittest.TestCase):
    def test_blocks_missing_or_unrecognised_confirmation(self):
        for tier in ('', 'free', 'true', 'internal', 'paid'):
            with self.subTest(tier=tier), self.assertRaises(ValueError):
                licensing.check({'FLUMP_AIR_LICENSE_TIER': tier})

    def test_explicit_eligible_free(self):
        self.assertIn('branding', licensing.check({'FLUMP_AIR_LICENSE_TIER': 'eligible-free'}))

    def test_paid_requires_licence(self):
        self.assertIn('SDK validates', licensing.check(
            {'FLUMP_AIR_LICENSE_TIER': 'paid', 'AIR_SDK_LICENSE_BASE64': 'test-placeholder'}))

    def test_rejects_conflicting_setup(self):
        with self.assertRaises(ValueError):
            licensing.check({'FLUMP_AIR_LICENSE_TIER': 'eligible-free',
                             'AIR_SDK_LICENSE_BASE64': 'test-placeholder'})


@unittest.skipUnless(platform.system() == 'Darwin' and platform.machine() == 'arm64',
                     'Native signing tests require macOS ARM64; no AIR SDK is used.')
class NativeSigningTests(unittest.TestCase):
    def test_zip_roundtrip_signatures_arm64_and_tamper_detection(self):
        with tempfile.TemporaryDirectory(prefix='flump-signing-test-') as temp:
            work = Path(temp)
            source = work / 'test.c'
            source.write_text('#include <stdio.h>\nint main(void) {\n'
                              '#ifdef __arm64__\nputs("native arm64"); return 0;\n'
                              '#else\nreturn 1;\n#endif\n}\n')
            app = work / 'Fixture.app'
            for bundle, name in ((app, 'Fixture'), (app / 'Contents/Helpers/Helper.app', 'Helper')):
                executable = bundle / 'Contents/MacOS' / name
                executable.parent.mkdir(parents=True)
                (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps(dict(
                    CFBundleExecutable=name, CFBundleIdentifier='flump.test.' + name,
                    CFBundlePackageType='APPL', CFBundleVersion='1')))
                run(['xcrun', 'clang', '-arch', 'arm64', '-arch', 'x86_64', source, '-o', executable])
            library = app / 'Contents/Frameworks/libfixture.dylib'
            library.parent.mkdir()
            run(['xcrun', 'clang', '-dynamiclib', '-arch', 'arm64', '-arch', 'x86_64',
                 source, '-o', library])
            resource = app / 'Contents/Resources/test.txt'
            resource.parent.mkdir()
            resource.write_text('original')
            sign(app)
            self.assertIn('libfixture.dylib', verify(app))
            archive = work / 'fixture.zip'
            run(['ditto', '-c', '-k', '--keepParent', app, archive])
            extracted = work / 'extracted'
            run(['ditto', '-x', '-k', archive, extracted])
            unpacked = extracted / app.name
            verify(unpacked)
            self.assertIn('native arm64', run(['/usr/bin/arch', '-arm64',
                                              unpacked / 'Contents/MacOS/Fixture']))
            (unpacked / 'Contents/Resources/test.txt').write_text('tampered')
            with self.assertRaises(RuntimeError):
                verify(unpacked)
            # A valid seal on the original still passes; modifying a binary fails too.
            binary = app / 'Contents/MacOS/Fixture'
            with binary.open('ab') as output:
                output.write(b'tampered')
            with self.assertRaises(RuntimeError):
                verify(app)


if __name__ == '__main__':
    unittest.main(verbosity=2)
