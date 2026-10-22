#!/usr/bin/env python3
"""Repackage the preserved signed AIR using current ADT, then ad-hoc sign on macOS.

This deliberately preserves the shipped SWF and requires no signing credentials.
It does not strip branding, patch ADT, or manually assemble the AIR runtime.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import zipfile

from macos_adhoc import run, sign, verify


def main():
    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location('license_check', root / 'bin/check-air-license.py')
    licensing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(licensing)
    print(licensing.check(os.environ))
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('Requires native ARM64 macOS; no Rosetta fallback.')
    os.chdir(root)
    report = root / 'exporter/build/ci/adhoc'
    report.mkdir(parents=True, exist_ok=True)
    source = root / 'exporter/dist/flump-exporter.air'
    with tempfile.TemporaryDirectory(prefix='flump-adhoc-') as temp:
        work = Path(temp)
        app = work / 'Flump.app'
        # Official ADT conversion embeds the current captive runtime and applies
        # its licensing. The existing AIR package already carries an AIR signature.
        try:
            result = run(['java', '-jar', Path(os.environ['AIR_HOME']) / 'lib/adt.jar',
                          '-package', '-target', 'bundle', app, source], timeout=300)
        except RuntimeError as error:
            (report / 'adt.txt').write_text(str(error), encoding='utf-8')
            raise RuntimeError('ADT could not convert the preserved AIR. See ci/adhoc/adt.txt. '
                               'No installer was created; no credential-free fallback is assumed.') from error
        (report / 'adt.txt').write_text(result, encoding='utf-8')
        if not (app / 'Contents/Frameworks/Adobe AIR.framework').is_dir():
            raise RuntimeError('ADT did not produce the expected captive-runtime application.')
        with zipfile.ZipFile(source) as signed_air:
            shipped = signed_air.read('flump-exporter.swf')
        payloads = list(app.rglob('flump-exporter.swf'))
        if len(payloads) != 1 or payloads[0].read_bytes() != shipped:
            raise RuntimeError('Packaged bytecode differs from the SWF inside the preserved signed AIR.')
        sign(app)
        (report / 'signatures.txt').write_text(verify(app), encoding='utf-8')
        shutil.copy2(root / 'docs/INSTALL-MAC-INTERNAL.txt', work)
        archive = work / 'Flump-mac-universal-internal.zip'
        staging = work / 'delivery'
        staging.mkdir()
        run(['/usr/bin/ditto', app, staging / app.name])
        shutil.copy2(work / 'INSTALL-MAC-INTERNAL.txt', staging)
        run(['/usr/bin/ditto', '-c', '-k', '--sequesterRsrc', staging, archive])
        # Verify and execute the ZIP's extracted app, not just the staging bundle.
        extracted = work / 'extracted'
        run(['/usr/bin/ditto', '-x', '-k', archive, extracted])
        final_app = extracted / 'Flump.app'
        (report / 'zip-signatures.txt').write_text(verify(final_app), encoding='utf-8')
        run([sys.executable, root / 'bin/ci-macos-smoke.py', '--app', final_app], timeout=420)
        # CLI smoke operates on a copy because Flump writes exporter.log in its app.
        verify(final_app)
        manifest = dict(source_commit=run(['git', 'rev-parse', 'HEAD']).strip(),
                        air_sdk='51.4.1.2', packaging='ADT signed-AIR conversion; native ad-hoc signing',
                        bytecode='SWF inside preserved exporter/dist/flump-exporter.air, not recompiled SWF',
                        air_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                        swf_sha256=hashlib.sha256(shipped).hexdigest(),
                        test='Extracted application exported squaredance under arch -arm64',
                        limitations='Finder/Gatekeeper first launch and GPU preview need M4 acceptance')
        output = root / 'exporter/build/internal-distribution'
        output.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archive, output)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        (output / (archive.name + '.sha256')).write_text(digest + '  ' + archive.name + '\n', encoding='utf-8')
        (output / 'build-info.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        print('Created and verified ' + str(output / archive.name))


if __name__ == '__main__':
    main()
