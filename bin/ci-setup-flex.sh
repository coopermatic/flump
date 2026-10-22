#!/bin/bash
# Intended for an ephemeral GitHub macOS ARM64 runner, not a designer's Mac.
set -euo pipefail
[[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]] || {
  echo 'This workflow requires a native Apple Silicon macOS runner.' >&2; exit 1;
}
: "${AIR_HOME:?AIR setup action must run first}"
: "${RUNNER_TEMP:?Run on a GitHub runner}"
tool_dir="$RUNNER_TEMP/flump-tools"
mkdir -p "$tool_dir" exporter/build/ci
curl --fail --location --retry 3 --silent --show-error \
  https://archive.apache.org/dist/ant/binaries/apache-ant-1.10.15-bin.zip -o "$tool_dir/ant.zip"
curl --fail --location --retry 3 --silent --show-error \
  https://archive.apache.org/dist/flex/4.16.1/binaries/apache-flex-sdk-4.16.1-bin.zip -o "$tool_dir/flex.zip"
echo "e59baf898dc5b6d1aa6cd57544715f7e0060b1fdc9e56f24f9898d56612a9e0b  $tool_dir/ant.zip" | shasum -a 256 -c -
echo "757aa19299c8a9c8af0901c1ae35f97fa94b7af0b0a9abc2bab04fe61d756e8b  $tool_dir/flex.zip" | shasum -a 256 -c -
unzip -q "$tool_dir/ant.zip" -d "$tool_dir"
mkdir "$tool_dir/flex"
unzip -q "$tool_dir/flex.zip" -d "$tool_dir/flex"
cp -R "$AIR_HOME/frameworks/libs/air/." "$tool_dir/flex/frameworks/libs/air/"
cp "$AIR_HOME/lib/afe.jar" "$AIR_HOME/lib/aglj40.jar" "$tool_dir/flex/lib/"
chmod +x "$tool_dir/apache-ant-1.10.15/bin/ant"
echo "FLEX_HOME=$tool_dir/flex" >> "$GITHUB_ENV"
echo "$tool_dir/apache-ant-1.10.15/bin" >> "$GITHUB_PATH"
version=$(java -jar "$AIR_HOME/lib/adt.jar" -version)
[[ "$version" == 51.4.1.2 ]] || { echo "Unexpected ADT version: $version" >&2; exit 1; }
{
  sw_vers
  uname -m
  java -version 2>&1
  echo "AIR $version"
  echo "Flex 4.16.1; Ant 1.10.15"
  shasum -a 256 "$AIR_HOME/lib/adt.jar" "$AIR_HOME/frameworks/libs/air/airglobal.swc"
  lipo -archs "$AIR_HOME/bin/adl"
} > exporter/build/ci/toolchain.txt
