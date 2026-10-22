"""Ad-hoc sign and strictly verify every native component, without a keychain."""
from pathlib import Path
import plistlib
import subprocess


def run(args, **kwargs):
    result = subprocess.run([str(arg) for arg in args], capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout + result.stderr


def inventory(app):
    app = Path(app).resolve()
    binaries = []
    bundles = []
    for path in app.rglob('*'):
        # Never follow an escaping symlink or sign the same file via its aliases.
        if not path.resolve().is_relative_to(app):
            raise RuntimeError('Bundle has an external symlink: ' + str(path))
        if path.is_symlink():
            continue
        if path.is_file() and 'Mach-O' in run(['/usr/bin/file', '-b', path]):
            binaries.append(path)
        elif path.is_dir() and path.suffix in ('.framework', '.app', '.xpc', '.appex', '.bundle'):
            bundles.append(path)
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    executable = app / 'Contents/MacOS' / info['CFBundleExecutable']
    if executable.resolve() not in {p.resolve() for p in binaries}:
        raise RuntimeError('Application executable is not a native binary in the bundle.')
    # Nested code first, enclosing framework/app last; do not use --deep for signing.
    bundles.sort(key=lambda path: len(path.parts), reverse=True)
    return binaries, bundles + [app]


def sign(app):
    binaries, bundles = inventory(app)
    for path in binaries + bundles:
        # Preserve SDK entitlements, but do not turn on hardened runtime or change
        # executable code, licence enforcement, splash screens or runtime resources.
        run(['/usr/bin/codesign', '--force', '--sign', '-', '--timestamp=none',
             '--preserve-metadata=entitlements', path])


def verify(app):
    app = Path(app).resolve()
    binaries, bundles = inventory(app)
    report = []
    for path in binaries:
        run(['/usr/bin/lipo', '-verify_arch', 'arm64', 'x86_64', path])
        run(['/usr/bin/codesign', '--verify', '--all-architectures', '--strict', path])
        for arch in ('arm64', 'x86_64'):
            details = run(['/usr/bin/codesign', '-d', '--verbose=4', '--arch', arch, path])
            if 'Signature=adhoc' not in details:
                raise RuntimeError('Missing ad-hoc signature for ' + arch + ': ' + str(path))
        report.append('Valid ad-hoc arm64 + x86_64: ' + str(path.relative_to(app)))
    for bundle in bundles:
        run(['/usr/bin/codesign', '--verify', '--deep', '--strict', '--all-architectures', bundle])
    report.append('All nested signatures and outer resource seal verified.')
    return '\n'.join(report) + '\n'
