"""Exercise real macOS packaging; only the unavailable Xcode archive is faked."""

import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


REPOSITORY = Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform == "darwin", "requires macOS packaging tools")
class BuildAndExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory(prefix="octocmd-fixtures-")
        cls.addClassCleanup(cls.fixtures.cleanup)
        directory = Path(cls.fixtures.name)
        for arch in ("arm64", "x86_64"):
            subprocess.run(
                ["xcrun", "clang", "-arch", arch, "-mmacosx-version-min=13.1",
                 "-x", "c", "-", "-o", str(directory / arch)],
                input="int main(void) { return 0; }\n", text=True, check=True,
                capture_output=True,
            )
        cls.universal = directory / "universal"
        cls.thin = directory / "arm64"
        subprocess.run(
            ["lipo", "-create", str(cls.thin), str(directory / "x86_64"),
             "-output", str(cls.universal)], check=True, capture_output=True,
        )

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="octocmd-build-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.project = self.directory / "checkout with spaces"
        self.project.mkdir()
        for name in ("build_and_export.sh", "LICENSE"):
            shutil.copy2(REPOSITORY / name, self.project / name)
        shutil.copytree(REPOSITORY / "OctoCmd.xcodeproj", self.project / "OctoCmd.xcodeproj")
        self.caller = self.directory / "caller"
        self.caller.mkdir()
        tools = self.directory / "bin"
        tools.mkdir()
        xcodebuild = tools / "xcodebuild"
        xcodebuild.write_text(f"#!{sys.executable}\n" + '''
import os
from pathlib import Path
import plistlib
import shutil
import sys

args = sys.argv[1:]
if args == ["-version"]:
    if os.environ.get("FAIL_PREFLIGHT"):
        sys.exit(1)
    print("Xcode 26.5")
    sys.exit(0)

if os.environ.get("FAIL_ARCHIVE"):
    sys.exit(71)

# Model only the archive boundary. The real script must package and validate it.
assert "archive" in args and "-exportArchive" not in args, args
for option, expected in (("-scheme", "OctoCmd"), ("-configuration", "Release"),
                         ("-destination", "generic/platform=macOS")):
    assert args[args.index(option) + 1] == expected, args
assert (Path(args[args.index("-project") + 1]) / "project.pbxproj").is_file(), args
assert "-derivedDataPath" in args, args
settings = dict(arg.split("=", 1) for arg in args if "=" in arg)
for key, value in (("ARCHS", "arm64 x86_64"), ("ONLY_ACTIVE_ARCH", "NO"),
                   ("CODE_SIGNING_ALLOWED", "NO"), ("DEVELOPMENT_TEAM", "")):
    assert settings.get(key) == value, settings

archive = Path(args[args.index("-archivePath") + 1])
archive.mkdir(parents=True, exist_ok=True)
if os.environ.get("MISSING_APP"):
    sys.exit(0)
app = archive / "Products/Applications/OctoCmd.app/Contents"
(app / "MacOS").mkdir(parents=True)
shutil.copy2(os.environ["FIXTURE_BINARY"], app / "MacOS/OctoCmd")
info = {
    "CFBundleExecutable": "OctoCmd",
    "CFBundleIdentifier": "test.octocmd.packaging",
    "CFBundlePackageType": "APPL",
    "CFBundleShortVersionString": settings.get("MARKETING_VERSION", "0.0.0"),
    "CFBundleVersion": settings.get("CURRENT_PROJECT_VERSION", "0"),
}
if os.environ.get("WRONG_VERSION"):
    info["CFBundleShortVersionString"] = "0.0.0"
(app / "Info.plist").write_bytes(plistlib.dumps(info))
''')
        xcodebuild.chmod(0o755)
        self.environment = os.environ.copy()
        for name in ("GITHUB_REF_TYPE", "GITHUB_REF_NAME", "VERSION", "BUILD_NUMBER",
                     "FAIL_PREFLIGHT", "FAIL_ARCHIVE", "MISSING_APP", "WRONG_VERSION"):
            self.environment.pop(name, None)
        self.environment.update(
            PATH=f"{tools}:{os.environ['PATH']}",
            FIXTURE_BINARY=str(self.universal),
            BUILD_NUMBER="42",
        )

    def run_build(self, from_elsewhere=False, **environment):
        return subprocess.run(
            ["bash", str(self.project / "build_and_export.sh")],
            cwd=self.caller if from_elsewhere else self.project,
            env={**self.environment, **environment},
            capture_output=True, text=True,
        )

    def assert_succeeded(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_tagged_build_packages_versioned_signed_universal_app_and_checksum(self):
        # Catches wrong tag/version propagation, lost permissions, missing signing,
        # omitted license, or a checksum that cannot verify the released ZIP.
        result = self.run_build(from_elsewhere=True, GITHUB_REF_TYPE="tag", GITHUB_REF_NAME="v1.2.3")
        self.assert_succeeded(result)
        package = self.project / "export/OctoCmd-1.2.3-macos-universal.zip"
        self.assertTrue(package.is_file())
        checksum = package.with_suffix(".zip.sha256").read_text().split()
        self.assertEqual(checksum, [hashlib.sha256(package.read_bytes()).hexdigest(), package.name])
        extracted = self.directory / "extracted"
        subprocess.run(["ditto", "-x", "-k", str(package), str(extracted)], check=True)
        app = extracted / "OctoCmd.app"
        info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
        self.assertEqual(info["CFBundleShortVersionString"], "1.2.3")
        self.assertEqual(info["CFBundleVersion"], "42")
        self.assertEqual((app / "Contents/Resources/LICENSE").read_bytes(),
                         (REPOSITORY / "LICENSE").read_bytes())
        binary = app / "Contents/MacOS/OctoCmd"
        self.assertTrue(os.access(binary, os.X_OK))
        for arch in ("arm64", "x86_64"):
            subprocess.run(["lipo", str(binary), "-verify_arch", arch], check=True)
        subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
        with zipfile.ZipFile(package) as contents:
            self.assertTrue(contents.getinfo("OctoCmd.app/Contents/MacOS/OctoCmd").external_attr >> 16 & 0o111)
        self.assertFalse((self.caller / "export").exists())

    def test_local_build_accepts_explicit_version(self):
        # Catches accidentally depending on GitHub-only version metadata.
        self.assert_succeeded(self.run_build(VERSION="2.0.1"))
        self.assertTrue((self.project / "export/OctoCmd-2.0.1-macos-universal.zip").is_file())

    def test_invalid_release_tag_is_rejected_before_outputs_are_touched(self):
        # Catches publishing a tag whose version cannot be represented in Info.plist.
        for tag in ("vnext", "v1.2", "v1.2.3-rc.1", "v1.2.3/unsafe"):
            with self.subTest(tag=tag):
                result = self.run_build(GITHUB_REF_TYPE="tag", GITHUB_REF_NAME=tag)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("vMAJOR.MINOR.PATCH", result.stderr)
                self.assertFalse((self.project / "archive").exists())

    def test_invalid_build_number_is_rejected(self):
        result = self.run_build(BUILD_NUMBER="not-a-number")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BUILD_NUMBER", result.stderr)
        self.assertFalse((self.project / "archive").exists())

    def test_missing_full_xcode_preserves_existing_outputs(self):
        # Catches the old command-v check accepting the Command Line Tools stub,
        # then deleting existing artifacts before discovering Xcode is absent.
        export = self.project / "export"
        export.mkdir()
        previous = export / "previous.zip"
        previous.write_text("keep me")
        result = self.run_build(FAIL_PREFLIGHT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Xcode", result.stderr)
        self.assertTrue(previous.is_file())
        self.assertEqual(previous.read_text(), "keep me")

    def test_archive_failure_does_not_produce_release_assets(self):
        result = self.run_build(FAIL_ARCHIVE="1")
        self.assertEqual(result.returncode, 71, result.stdout + result.stderr)
        self.assertEqual(list(self.project.glob("export/*.zip")), [])

    def test_single_architecture_archive_is_not_published_as_universal(self):
        result = self.run_build(FIXTURE_BINARY=str(self.thin))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.project.glob("export/*.zip")), [])

    def test_missing_app_is_reported_before_packaging(self):
        result = self.run_build(MISSING_APP="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OctoCmd.app", result.stderr)
        self.assertEqual(list(self.project.glob("export/*.zip")), [])

    def test_version_mismatch_is_not_published(self):
        result = self.run_build(WRONG_VERSION="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version", result.stderr.lower())
        self.assertEqual(list(self.project.glob("export/*.zip")), [])


if __name__ == "__main__":
    unittest.main()
