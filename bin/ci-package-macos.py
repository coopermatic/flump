#!/usr/bin/env python3
"""Sign on an ephemeral macOS runner using existing credentials supplied as secrets.

No certificates or private keys are generated. The random password below only
locks a disposable local Keychain, which is deleted in finally.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import subprocess
import sys
import tempfile
import zipfile

REQUIRED = ('APPLE_DEVELOPER_ID_P12_BASE64', 'APPLE_DEVELOPER_ID_P12_PASSWORD',
            'APPLE_SIGNING_IDENTITY', 'APPLE_NOTARY_KEY_BASE64',
            'APPLE_NOTARY_KEY_ID', 'APPLE_NOTARY_ISSUER_ID')


def preflight(kind):
    required = list(REQUIRED)
    if kind == 'air4mac':
        required += ['AIR_SIGNING_P12_BASE64', 'AIR_SIGNING_P12_PASSWORD', 'AIR_TIMESTAMP_URL']
    missing = [name for name in required if not os.environ.get(name)]
    if os.environ.get('AIR_LICENSE_CONFIRMED') != 'true':
        missing.append('AIR_LICENSE_CONFIRMED=true (owner confirms appropriate AIR licence)')
    if missing:
        raise RuntimeError('Missing configuration: ' + ', '.join(missing))
    if not os.environ['APPLE_SIGNING_IDENTITY'].startswith('Developer ID Application: '):
        raise RuntimeError('Use a Developer ID Application identity, not Apple Development/Distribution.')
    if kind == 'air4mac' and os.environ['AIR_TIMESTAMP_URL'] == 'none':
        raise RuntimeError('A distribution AIR signature requires an approved timestamp service.')


def run(args, **kwargs):
    # Never print full argv: security import requires a password argument.
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True, **kwargs)
    if result.returncode:
        # ADT and Apple errors are useful, but redact supplied secrets defensively.
        message = result.stdout + result.stderr
        for name in (*REQUIRED, 'AIR_SIGNING_P12_BASE64', 'AIR_SIGNING_P12_PASSWORD'):
            value = os.environ.get(name)
            if value:
                message = message.replace(value, '[REDACTED]')
        raise RuntimeError(Path(str(args[0])).name + ' failed:\n' + message)
    return result.stdout


def decode(name, path):
    path.write_bytes(base64.b64decode(os.environ[name], validate=True))
    path.chmod(0o600)


def notarize(archive, label, private, report):
    auth = ['--key', private / 'notary.p8', '--key-id', os.environ['APPLE_NOTARY_KEY_ID'],
            '--issuer', os.environ['APPLE_NOTARY_ISSUER_ID']]
    # Keep the submission ID even if the service reports Invalid or times out.
    result = subprocess.run(['xcrun', 'notarytool', 'submit', str(archive), *map(str, auth),
                             '--wait', '--timeout', '20m', '--output-format', 'json'],
                            capture_output=True, text=True, timeout=1300)
    try:
        submission = json.loads(result.stdout)
    except ValueError:
        raise RuntimeError('Notary service returned no submission JSON; check Apple credentials/service.')
    (report / (label + '-notary.json')).write_text(json.dumps(submission, indent=2), encoding='utf-8')
    if submission.get('id') and submission.get('status') in ('Accepted', 'Invalid', 'Rejected'):
        run(['xcrun', 'notarytool', 'log', submission['id'], *auth,
             report / (label + '-notary-log.json')])
    if result.returncode or submission.get('status') != 'Accepted':
        raise RuntimeError(label + ' notarisation is not Accepted; see saved submission/log. Do not distribute.')
    return submission


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', nargs='?', choices=('app', 'air4mac'), default='app')
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    preflight(args.kind)
    if args.preflight:
        print('Required configuration is present; credential validity is checked by Apple during signing.')
        return
    if platform.system() != 'Darwin' or platform.machine() != 'arm64' or os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Signing is restricted to an ephemeral GitHub macOS ARM64 runner.')
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    report = root / 'exporter/build/ci'
    report.mkdir(parents=True, exist_ok=True)
    identity = os.environ['APPLE_SIGNING_IDENTITY']
    old_default = run(['security', 'default-keychain', '-d', 'user']).strip().strip('"')
    old_search = run(['security', 'list-keychains', '-d', 'user']).splitlines()
    old_search = [p.strip().strip('"') for p in old_search]
    with tempfile.TemporaryDirectory(prefix='flump-signing-', dir=os.environ['RUNNER_TEMP']) as temp:
        private = Path(temp)
        keychain = private / 'build.keychain-db'
        password = secrets.token_hex(32)
        try:
            decode('APPLE_DEVELOPER_ID_P12_BASE64', private / 'developer-id.p12')
            decode('APPLE_NOTARY_KEY_BASE64', private / 'notary.p8')
            run(['security', 'create-keychain', '-p', password, keychain])
            run(['security', 'set-keychain-settings', '-lut', '3600', keychain])
            run(['security', 'unlock-keychain', '-p', password, keychain])
            run(['security', 'import', private / 'developer-id.p12', '-k', keychain,
                 '-P', os.environ['APPLE_DEVELOPER_ID_P12_PASSWORD'], '-T', '/usr/bin/codesign',
                 '-T', '/usr/bin/security'])
            run(['security', 'set-key-partition-list', '-S', 'apple-tool:,apple:,codesign:',
                 '-s', '-k', password, keychain])
            run(['security', 'list-keychains', '-d', 'user', '-s', keychain, *old_search])
            run(['security', 'default-keychain', '-d', 'user', '-s', keychain])
            identities = run(['security', 'find-identity', '-v', '-p', 'codesigning', keychain])
            if identity not in identities:
                raise RuntimeError('Requested Developer ID identity is not a valid signing identity in the supplied P12.')
            if args.kind == 'app':
                app = root / 'exporter/build/macos/Flump.app'
                app.parent.mkdir(parents=True, exist_ok=True)
                # Read the AIR-signing key from PKCS12 via stdin to avoid a Java
                # Keychain private-key access prompt on a noninteractive runner.
                # Native codesign still uses the imported Developer ID identity.
                run(['java', '-jar', Path(os.environ['AIR_HOME']) / 'lib/adt.jar', '-package',
                     '-storetype', 'pkcs12', '-keystore', private / 'developer-id.p12', '-tsa', 'none',
                     '-target', 'bundle', '-storetype', 'KeychainStore', '-alias', identity,
                     app, 'etc/airdesc.xml', 'icons/icon_16.png', 'icons/icon_32.png',
                     'icons/icon_48.png', 'icons/icon_128.png', '-C', 'build', 'flump-exporter.swf'],
                    cwd=root / 'exporter', input=os.environ['APPLE_DEVELOPER_ID_P12_PASSWORD'] + '\n')
                verification = run(['bash', 'bin/verify-macos.sh', app])
                (report / 'bundle-verification.txt').write_text(verification, encoding='utf-8')
                # The smoke script runs a copy because existing CLI logging mutates its app directory.
                run([sys.executable, 'bin/ci-macos-smoke.py', '--app', app], timeout=420)
                run(['codesign', '--verify', '--deep', '--strict', app])
                upload = private / 'Flump-notarize.zip'
                run(['ditto', '-c', '-k', '--keepParent', app, upload])
                notarize(upload, 'app', private, report)
                run(['xcrun', 'stapler', 'staple', app])
                run(['xcrun', 'stapler', 'validate', app])
                run(['spctl', '--assess', '--type', 'execute', '--verbose=4', app])
                output = root / 'exporter/build/distribution'
                output.mkdir(parents=True, exist_ok=True)
                archive = output / 'Flump-mac-universal.zip'
                run(['ditto', '-c', '-k', '--keepParent', app, archive])
                shutil.copy2(root / 'docs/INSTALL-MAC.txt', output)
            else:
                decode('AIR_SIGNING_P12_BASE64', private / 'air.p12')
                air = private / 'Flump.air'
                # AIR identity is independent from Apple's native Developer ID identity.
                # Retain the old AIR identity for updates only if it is still approved/valid.
                run(['java', '-jar', Path(os.environ['AIR_HOME']) / 'lib/adt.jar', '-package',
                     '-storetype', 'pkcs12', '-keystore', private / 'air.p12',
                     '-tsa', os.environ['AIR_TIMESTAMP_URL'], '-target', 'air4mac',
                     '-storetype', 'KeychainStore', '-alias', identity, air, 'etc/airdesc.xml',
                     'icons/icon_16.png', 'icons/icon_32.png', 'icons/icon_48.png', 'icons/icon_128.png',
                     '-C', 'build', 'flump-exporter.swf'],
                    cwd=root / 'exporter', input=os.environ['AIR_SIGNING_P12_PASSWORD'] + '\n')
                # Apple does not accept .air as a top-level submission format. Test a ZIP
                # wrapper, without rewriting signed AIR contents or claiming stapling support.
                upload = private / 'Flump-air4mac-notarize.zip'
                with zipfile.ZipFile(upload, 'w', zipfile.ZIP_DEFLATED) as z:
                    z.write(air, 'Flump.air')
                notarize(upload, 'air4mac', private, report)
                log = json.loads((report / 'air4mac-notary-log.json').read_text(encoding='utf-8'))
                if not log.get('ticketContents'):
                    raise RuntimeError('Apple issued no code tickets for air4mac; use the notarised standalone ZIP.')
                output = root / 'exporter/build/air4mac-validation'
                output.mkdir(parents=True, exist_ok=True)
                archive = output / 'Flump.air'
                shutil.copy2(air, archive)
                (output / 'VALIDATION-REQUIRED.txt').write_text(
                    'Signed air4mac candidate. Not yet cleared for designer distribution.\n'
                    'The build owner must verify shared-runtime installation, installed code signature,\n'
                    'Gatekeeper and native ARM64 launch on a clean Mac test environment.\n'
                    'No stapling of .air is claimed. Use the notarised standalone ZIP if this route fails.\n',
                    encoding='utf-8')
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            (output / (archive.name + '.sha256')).write_text(digest + '  ' + archive.name + '\n', encoding='utf-8')
            print('Created ' + str(archive.relative_to(root)))
        finally:
            # These are only paths recorded/created above, on this disposable runner.
            subprocess.run(['security', 'default-keychain', '-d', 'user', '-s', old_default], capture_output=True)
            subprocess.run(['security', 'list-keychains', '-d', 'user', '-s', *old_search], capture_output=True)
            if keychain.exists():
                subprocess.run(['security', 'delete-keychain', str(keychain)], capture_output=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
