# OctoCmd

<img width="1240" height="640" alt="Frame 3" src="https://github.com/user-attachments/assets/8fed306b-5ca5-4ca9-8ca2-9c9874131d4c" />

A blazingly fast productivity tool for macOS. Switch apps, search screen text, and navigate windows without leaving your keyboard.

## What is this?

**OctoCmd** is an open-source productivity suite, inspired by [rcmd](https://lowtechguys.com/rcmd/) and [Vimium](https://vimium.github.io/). It evolves beyond a simple app switcher into a comprehensive keyboard-driven navigation tool.

This is the independently maintained [senilio/OctoCmd](https://github.com/senilio/OctoCmd) fork of [huytd/OctoCmd](https://github.com/huytd/OctoCmd). Original attribution and the Apache-2.0 license are retained.

## Download and install

Download the universal macOS ZIP and matching `.sha256` file from [Releases](https://github.com/senilio/OctoCmd/releases). Builds support Apple Silicon and Intel on macOS 13.1 or newer.

Verify the download from the directory containing both files, then extract the ZIP and move `OctoCmd.app` into Applications:

```sh
shasum -a 256 -c OctoCmd-*-macos-universal.zip.sha256
```

**These are preview builds:** they are ad-hoc signed, not Developer ID signed or notarized. macOS may block first launch. If you trust the download, attempt to open the app, then use **System Settings → Privacy & Security → Open Anyway** if offered. Managed Macs may prohibit this override.

Grant **Accessibility** permission when prompted for keyboard control and cross-application navigation. Screen-text search also needs **Screen Recording** permission in Privacy & Security. Permission approval may need to be repeated after updating an ad-hoc-signed build.

## Build and release

A full Xcode installation is required to build the app; Command Line Tools alone are insufficient. CI uses macOS 26 with Xcode 26.5. From a checkout:

```sh
VERSION=1.0.0 BUILD_NUMBER=1 ./build_and_export.sh
```

The script can also be invoked from another working directory. It builds both architectures, checks the application version, includes the license, ad-hoc signs the bundle, and writes a ZIP plus SHA-256 checksum into `export/`. It replaces previous archive/export outputs after validating its inputs and checking Xcode. No Apple account or signing secrets are required.

Run the build-script tests on macOS with:

```sh
python3 -B -m unittest discover -s tests -v
```

These tests simulate Xcode's archive step but use real macOS binaries, signing, and packaging tools. The workflow additionally archives the actual application.

Pushes to `master`, pull requests, and manual workflow runs produce downloadable Actions artifacts. To publish a release after CI is green on `master`, tag that commit using **`vMAJOR.MINOR.PATCH`** and push the tag to your fork, for example:

```sh
git tag v1.0.0
git push origin v1.0.0
```

The tag determines the application version; the workflow run number supplies its build number. A separate tag-only job verifies checksums and publishes the ZIP and checksum to this repository's GitHub Releases using `GITHUB_TOKEN`. Pull-request builds have read-only repository permissions and cannot publish releases. Prerelease tag suffixes are not supported yet.

Developer ID signing and notarization are not configured yet; those require the maintainer's Apple Developer credentials.

## Key Features

- **App Switcher:** Blazingly fast app switching using the first letter of the application name.
- **Search Mode:** Search for any text visible on your screen and click it instantly.
- **Link Hints:** Keyboard-driven clicking for buttons, links, and UI elements (Vimium-style).
- **Scroll Mode:** Navigate and scroll through windows using `j`/`k` or arrow keys.
- **App Groups:** Group related applications together to activate them with a single keystroke.
- **Pinning:** Keep your most-used apps always visible in the switcher.
- **Electron Support:** Enhanced accessibility for Electron apps like Slack, Discord, and VS Code.

## How to use?

### App Switching

<img width="752" height="484" alt="image" src="https://github.com/user-attachments/assets/d15f94dd-7cb9-4c50-a800-9ccd0cf688fd" />

At any time, hit the **Right Command** <kbd>⌘</kbd> key to bring up the main screen. From here, press any letter to jump to the corresponding application.

- <kbd>Right ⌘ + C</kbd> for **Google Chrome**
- <kbd>Right ⌘ + F</kbd> for **Firefox**
- <kbd>Right ⌘ + I</kbd> for **IntelliJ IDEA**

### Search Mode

<img width="1728" height="1117" alt="image" src="https://github.com/user-attachments/assets/2daa3254-e971-4858-84ef-7f64d6e7d5de" />

<img width="1728" height="1117" alt="image" src="https://github.com/user-attachments/assets/a097e720-a25a-4d55-8405-f54a57dec871" />

Hit <kbd>⇧ + Space</kbd> (default) to enter Search Mode. Type any text you see on the screen to highlight it.
- Press <kbd>Enter</kbd> to click on the selected result.
- Use <kbd>AA</kbd>, <kbd>AB</kbd>, etc., hints to jump directly to clickable elements.

### Scroll Mode

Hit <kbd>⌃ + S</kbd> (default) to enter Scroll Mode. The active scrollable area will be highlighted with a blue border.
- Use <kbd>j</kbd>/<kbd>k</kbd> or <kbd>↑</kbd>/<kbd>↓</kbd> to scroll.
- Use <kbd>h</kbd>/<kbd>l</kbd> or <kbd>←</kbd>/<kbd>→</kbd> for horizontal scrolling.
- Press <kbd>Tab</kbd> to cycle between different scrollable areas in the window.

### Navigation

Within the OctoCmd window, use these shortcuts to switch pages:
- <kbd>⌘ + 1</kbd>: Active Apps
- <kbd>⌘ + 2</kbd>: Skipped Apps
- <kbd>⌘ + 3</kbd>: App Groups
- <kbd>⌘ + 4</kbd>: Settings

Hit <kbd>ESC</kbd> to dismiss the window or <kbd>⌘ + Q</kbd> to quit.

## Settings
OctoCmd is highly customizable. You can change activation shortcuts for all modes in the **Settings** tab (<kbd>⌘ + 4</kbd>). Double-click on any shortcut to record a new one.
