#!/bin/bash

# Build a universal, ad-hoc-signed macOS preview without Apple credentials.
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVE_PATH="$ROOT_DIR/archive/OctoCmd.xcarchive"
EXPORT_DIR="$ROOT_DIR/export"
APP_PATH="$EXPORT_DIR/OctoCmd.app"
VERSION_PATTERN='[0-9]+\.[0-9]+\.[0-9]+'

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

if [[ "${GITHUB_REF_TYPE:-}" == "tag" ]]; then
    TAG="${GITHUB_REF_NAME:-}"
    [[ "$TAG" =~ ^v${VERSION_PATTERN}$ ]] || die "Release tags must use vMAJOR.MINOR.PATCH (for example v1.0.0)."
    VERSION="${TAG#v}"
else
    VERSION="${VERSION:-1.0.0}"
fi
[[ "$VERSION" =~ ^${VERSION_PATTERN}$ ]] || die "VERSION must use MAJOR.MINOR.PATCH."
BUILD_NUMBER="${BUILD_NUMBER:-1}"
[[ "$BUILD_NUMBER" =~ ^[1-9][0-9]*$ ]] || die "BUILD_NUMBER must be a positive integer."

# Do not remove previous artifacts until we know a full Xcode is selected.
xcodebuild -version || die "Full Xcode is required. Install Xcode and select it with xcode-select or DEVELOPER_DIR."
[[ -f "$ROOT_DIR/OctoCmd.xcodeproj/project.pbxproj" ]] || die "OctoCmd.xcodeproj is missing."

rm -rf "$ARCHIVE_PATH" "$EXPORT_DIR"
mkdir -p "$ROOT_DIR/archive" "$EXPORT_DIR"

xcodebuild \
    -project "$ROOT_DIR/OctoCmd.xcodeproj" \
    -scheme OctoCmd \
    -configuration Release \
    -destination 'generic/platform=macOS' \
    -derivedDataPath "$ROOT_DIR/build/DerivedData" \
    -archivePath "$ARCHIVE_PATH" \
    archive \
    'ARCHS=arm64 x86_64' \
    ONLY_ACTIVE_ARCH=NO \
    CODE_SIGN_IDENTITY= \
    CODE_SIGNING_REQUIRED=NO \
    CODE_SIGNING_ALLOWED=NO \
    DEVELOPMENT_TEAM= \
    "MARKETING_VERSION=$VERSION" \
    "CURRENT_PROJECT_VERSION=$BUILD_NUMBER"

# An unsigned archive does not need Xcode's distribution export/signing flow.
ARCHIVED_APP="$ARCHIVE_PATH/Products/Applications/OctoCmd.app"
[[ -d "$ARCHIVED_APP" ]] || die "Archive does not contain OctoCmd.app."
ditto "$ARCHIVED_APP" "$APP_PATH"

lipo "$APP_PATH/Contents/MacOS/OctoCmd" -verify_arch arm64
lipo "$APP_PATH/Contents/MacOS/OctoCmd" -verify_arch x86_64
[[ "$(plutil -extract CFBundleShortVersionString raw -o - "$APP_PATH/Contents/Info.plist")" == "$VERSION" ]] || die "Archived application version does not match $VERSION."
[[ "$(plutil -extract CFBundleVersion raw -o - "$APP_PATH/Contents/Info.plist")" == "$BUILD_NUMBER" ]] || die "Archived application build number does not match $BUILD_NUMBER."

mkdir -p "$APP_PATH/Contents/Resources"
cp "$ROOT_DIR/LICENSE" "$APP_PATH/Contents/Resources/LICENSE"
# Seal the complete bundle, including its license. This is not Developer ID signing.
codesign --force --sign - --timestamp=none "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

PACKAGE_NAME="OctoCmd-${VERSION}-macos-universal.zip"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$EXPORT_DIR/$PACKAGE_NAME"
(
    cd -- "$EXPORT_DIR"
    shasum -a 256 "$PACKAGE_NAME" > "$PACKAGE_NAME.sha256"
)

printf '\nCreated %s\nChecksum: %s\n' "$EXPORT_DIR/$PACKAGE_NAME" "$EXPORT_DIR/$PACKAGE_NAME.sha256"
printf 'Preview build: ad-hoc signed, not notarized. macOS may block first launch.\n'
