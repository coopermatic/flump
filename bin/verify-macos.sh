#!/bin/bash
# Run with bash on macOS. This verifies the artifact, not the running process.
set -euo pipefail
app="${1:?Usage: bash bin/verify-macos.sh /path/to/Flump.app}"
if [[ "$(uname -s)" != Darwin ]]; then
  echo "Run this check on macOS." >&2
  exit 1
fi
executable=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$app/Contents/Info.plist")
test -f "$app/Contents/MacOS/$executable"
test -d "$app/Contents/Frameworks/Adobe AIR.framework"
count=0
while IFS= read -r -d '' binary; do
  if /usr/bin/file -b "$binary" | /usr/bin/grep -q 'Mach-O'; then
    /usr/bin/lipo "$binary" -verify_arch arm64 x86_64
    printf 'Universal: %s\n' "$binary"
    count=$((count + 1))
  fi
done < <(/usr/bin/find "$app/Contents" -type f -print0)
if [[ "$count" -lt 2 ]]; then
  echo "Expected at least an application executable and an AIR runtime binary." >&2
  exit 1
fi
/usr/bin/codesign --verify --deep --strict --verbose=2 "$app"
/usr/bin/codesign -dv --verbose=4 "$app"
echo 'Artifact checks passed. Now launch on Apple Silicon and confirm Kind = Apple in Activity Monitor.'
echo 'A universal binary alone does not prove that a running process avoided Rosetta.'
