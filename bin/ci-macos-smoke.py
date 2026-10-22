#!/usr/bin/env python3
"""Native Mac smoke test on an ephemeral runner; never touches original assets.

With --app, test a COPY: Flump's existing CLI writes exporter.log inside its
application directory, which must not mutate the signed distribution bundle.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile


def make_config(work, name):
    exports = []
    for folder, fmt in [('json', 'JSON'), ('jsonzip', 'JSONZip')]:
        exports.append(dict(name=folder, format=fmt, scale=1, scaleFactors=[1],
                            textureBorder=1, maxAtlasSize=2048, optimize='Memory',
                            quality='best', prettyPrint=False, combine=False))
    config = work / (name + '.flump')
    config.write_text(json.dumps(dict(importDir='resources', exportDir=name + '-export',
                                      exports=exports)), encoding='utf-8')
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path)
    args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        parser.error('Requires a native ARM64 macOS runner; no Rosetta fallback.')
    root = Path(__file__).resolve().parent.parent
    report = root / 'exporter/build/ci' / ('packaged-smoke' if args.app else 'adl-smoke')
    report.mkdir(parents=True, exist_ok=True)
    adl = str(Path(os.environ['AIR_HOME']) / 'bin/adl')
    with tempfile.TemporaryDirectory(prefix='flump-smoke-') as temp:
        work = Path(temp)
        resources = work / 'resources'
        resources.mkdir()
        fixtures = root / 'exporter/src/test/resources'
        shutil.copytree(fixtures / 'squaredance', resources / 'squaredance')
        shutil.copy2(fixtures / 'squaredance.swf', resources)
        for label in ('baseline', 'candidate'):
            config = make_config(work, label)
            if label == 'candidate' and args.app:
                app = work / 'Flump.app'
                shutil.copytree(args.app.resolve(), app, symlinks=True)
                info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
                command = [str(app / 'Contents/MacOS' / info['CFBundleExecutable']),
                           '--export', str(config), '--unmodified']
                app_dir = app
            else:
                app_dir = work / (label + '-app')
                app_dir.mkdir()
                source = root / ('exporter/dist' if label == 'baseline' else 'exporter/build')
                shutil.copy2(source / 'flump-exporter.swf', app_dir)
                shutil.copytree(root / 'exporter/icons', app_dir / 'icons')
                descriptor = (root / 'exporter/etc/airdesc.xml').read_text(encoding='utf-8')
                descriptor = descriptor.replace('<id>flump</id>', '<id>flump.ci.' + label + '</id>')
                (app_dir / 'application.xml').write_text(descriptor, encoding='utf-8')
                command = [adl, str(app_dir / 'application.xml'), str(app_dir),
                           '--', '--export', str(config), '--unmodified']
            # exec fails if an ARM64 slice cannot run; it cannot translate to x86_64.
            command = ['/usr/bin/arch', '-arm64', *command]
            result = subprocess.run(command, capture_output=True, text=True, timeout=180)
            (report / (label + '-stdout.txt')).write_text(
                result.stdout + result.stderr + '\nExit: ' + str(result.returncode), encoding='utf-8')
            logs = list(app_dir.rglob('exporter.log'))
            complete = False
            for i, log in enumerate(logs):
                content = log.read_text(encoding='utf-8')
                (report / (label + '-exporter-' + str(i) + '.txt')).write_text(content, encoding='utf-8')
                complete |= 'Publishing complete.' in content
            if result.returncode or not complete:
                raise RuntimeError(label + ' export did not complete; see smoke logs')
            output = work / (label + '-export')
            shutil.copytree(output, report / (label + '-export'), dirs_exist_ok=True)
            expected = {'json/squaredance/library.json', 'jsonzip/squaredance.zip'}
            actual = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}
            if not expected <= actual or not any(p.endswith('.png') for p in actual):
                raise RuntimeError('Missing expected JSON, ZIP or PNG export')
        result = subprocess.run([sys.executable, str(root / 'bin/compare-exports.py'),
                                 str(work / 'baseline-export'), str(work / 'candidate-export')],
                                capture_output=True, text=True)
        (report / 'comparison.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
        print(result.stdout)
        result.check_returncode()
    print('Native ARM64 export smoke passed; this does not replace designer acceptance testing.')


if __name__ == '__main__':
    main()
