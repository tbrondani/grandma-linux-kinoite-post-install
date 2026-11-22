# Development status

The initial installation path has been exercised on Fedora Kinoite 45 with Plasma 6.8.3 and Wayland in the development VM. This is not a release qualification or a physical hardware test.

## Implemented and checked

- English and Brazilian Portuguese setup messages and localized launchers.
- Git-free archive bootstrap, tested locally with download fixtures.
- Kinoite, Plasma 6, Wayland, and architecture checks.
- Batched installation of restic, Vim, Fastfetch, BLAKE3 verification and Python desktop bindings, with a reboot boundary.
- Curated apps and games; existing native and Flatpak apps are preserved.
- User-scope Flathub with app availability checks.
- Selected desktop shortcuts, WhatsApp launcher, and explicit Flatpak icon paths.
- Task folders in the application menu and default file associations.
- Double-click behavior, disabled middle-click paste, and Flameshot auto-save configuration.
- Se7en Aero 3.1 with pinned KDE Store components, bottom panel, and column layout. The user wallpaper is preserved.
- Guest validation, application startup probes, repeat-run checks, and JSON reports.
- Ten offline dictionaries for Portuguese ↔ Spanish, French, English, German, and Italian; real lookups passed with Flatpak network access disabled.
- RustDesk in the Help menu, with temporary-password defaults and no autostart.
- Night light from 19:00 to 05:00, 4500 K, with 30-minute transitions. Dictionary moved to Utilities.
- Test VM SSH and Plasma Login Manager auto-login, checked after reboot.

- Offline Argos sentence translation: ten directions and the localized GUI passed with network isolation; see [Translator](TRANSLATOR.md).
- Per-item storage inventory and download estimates: see [Installation size](INSTALLATION-SIZE.md).

- Local restic file backup, monthly timer, 12 monthly/3 yearly retention and recovery into new folders; see [Backup](BACKUP.md).
- Offline bilingual User manual as a standalone HTML book: chapters, favorites, language switching, light/dark themes and text enlargement. Three-choice Help, support information and an Updates menu for Discover and stable project releases remain available; see [Help](HELP.md).

## Latest development VM results

On 2026-11-21, the baseline deployment reached one Organic Maps compatibility failure. After updating catalogue/hash support and rebooting, setup and validation both exited 0; all 146 checks passed. Maria logged in automatically after reboot. The English and PT-BR manual pages were opened and visually checked in the desktop. Logs and execution JSON are saved in test-results. In the earlier development run, all 26 application startup probes passed with Se7en Aero. A KWallet prompt required user interaction during the run; this is not a fully unattended first-use acceptance test. Repeating setup preserved generated files, app inventory, and OSTree deployments. These probes do not prove every application's features work.

The HTML manual update passed 147 read-only VM checks. Browser tests covered offline loading, favorites across browser restarts, language/theme persistence and 200% text reflow. The installed Brave Flatpak loaded the desktop HTML file without new permissions. The maintainer approved the desktop visual review after the clean deployment and update test on 2026-11-21.

## Pending before v0.1.0

- Repeat hardware-specific acceptance on the target computer. The 2026-11-21 clean baseline restore, offline login preparation, installation, reboot/resume and local update fixture all passed; the saved baseline was preserved.


- Recreate a VM from installation media to qualify provisioning. The latest setup run started from the saved clean Fedora base, with SSH and automatic login prepared first.
- Physical hardware, camera, microphone, audio, suspend, and networking tests.
- Desktop visual review approved by the maintainer in the VM; verify scaling and readability on the target display.
- First-use KWallet prompts under test VM auto-login. Keep credential storage enabled; startup probes do not prove a prompt-free first launch.
- Brave feature reduction and end-to-end web app tests.
- Physical-disk reinstall and off-device copy checks for local backup; see BACKUP.md. Local copy, retention, safe restore and a simulated new installation have passed in the VM.
- RustDesk real incoming connection and Wayland permission tests. Installation, temporary-password defaults, no autostart, minimizing without disconnecting, and shutdown after closing the main window have been checked through KWin, without input injection.
- Local AI deployment and resource tests.
- Portugal maps: four files downloaded and verified against the installed catalogue. Offline rendering, routing and search still need a visual check. Select Brazilian states before adding their downloads; see OFFLINE.md.
- Complete upstream license inventory and translated contributor guides.
- Optional Windows 10-style preset. The current Se7en Aero appearance has been approved.

## Backlog

- Reader acceptance on the physical monitor remains pending. Setup installs pinned Atkinson Hyperlegible Next fonts under OFL-1.1 and offers reversible 12/14 pt presets in System → Reading comfort; see [Reading comfort](ACCESSIBILITY.md). Compare these with the existing font at a normal reading distance. The current desktop font is kept until the user chooses a preset.

- Project helper study: benchmark a small quantized multilingual model with [llamafile](https://www.mozilla.ai/open-tools/llamafile), starting with a 1–2B model candidate such as [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct). Use only the public manual and selected project guides as reference material. Prefer a small local text index to an additional embedding model. Show the supporting manual section with each answer; say when no section answers the question. Run on demand, bind only to localhost, and provide no shell tools or system control. Measure download, disk, peak RAM, first-token time and PT-BR/English answer quality on the seventh-generation i5 with 8 GB. The model and retrieval layer are not installed yet.

- Evaluate a separate `/var/home` for new Fedora installations in a separate VM. The current development VM uses ext4 with home on the system filesystem. Keep post-install compatible with both layouts; do not repartition existing installations. Local versioned backups remain necessary.

- Complete clean-baseline size and traffic measurements. A dated per-item inventory is available in INSTALLATION-SIZE.md; exact additional disk use and captured setup traffic still need a before/after run. Test translation speed and memory on the seventh-generation i5 with 8 GB RAM.

Se7en Aero is installed directly from KDE Store. `data/themes.json` pins the five reviewed downloads by SHA-256. Theme archives and assets are not bundled in this repository. Upstream layout scripts are not executed and wallpaper dependencies are not installed. The chat launcher uses an original MIT icon.

References: [Flatpak commands](https://docs.flatpak.org/en/latest/flatpak-command-reference.html), [rpm-ostree](https://github.com/coreos/rpm-ostree/blob/main/docs/administrator-handbook.md), [AeroThemePlasma installation](https://github.com/aeroshell-desktop/aerothemeplasma/blob/Plasma/6.8/INSTALL.md), [Plasma Login Manager](https://github.com/KDE/plasma-login-manager).

The remote-support launcher requires Python D-Bus and GLib, installed through the system package stage. It observes the main RustDesk window through KWin and stops the sandbox when that window closes. It does not use xdotool. A compositor restart also stops support.

The VM preflight queries the Plasma version with the offscreen Qt backend. The guest runner waits for both plasmashell and KWin before setup; a graphical startup race must not be reported as an unsupported Plasma version.

After the Plasma preflight fix on 2026-11-21, the restored VM completed setup and validation with exit code 0 after the package deployment reboot. All 147 checks passed. Evidence: `test-results/plasma-retry-execution.json` and `test-results/plasma-retry-after-reboot.log` (local, ignored).

The project updater passed a real installer run in the VM with a local release fixture: SHA256 validation, safe extraction, version recording, personal-file preservation and appearance/backup settings preservation. Live Plasma icon-position caches are excluded from the comparison. No stable GitHub release is published yet; production release download acceptance remains pending.

Checkpoint before backlog work: the latest clean deployment (`deploy-20261121T230133Z-F7bPl9`) passed all 147 checks and the local update fixture. The Stanza SyntaxWarning did not interrupt installation. The maintainer approved the visual result.

On 2026-11-22, 7 Icons (Win2-7) replaced the Win11 icon default. ZIP aliases are preserved and unsafe links are rejected; the package uses the installed Breeze fallback. The existing VM installation passed 154 checks. Both reading presets and restoration of the original per-key settings passed on the VM. Qt rendered the actual icon aliases, accented Portuguese text and both font families. No fresh-baseline run or physical reader acceptance is claimed for these changes.

## Feature-round updater completion (2026-11-22)

The desktop Updates shortcut now shows the installed version, offers project updates separately from Discover, displays native progress, and opens the update log. Project updates preserve appearance, reading and backup settings and existing launchers. New app launchers and theme assets are installed without selecting a different desktop appearance.

The verified archive and pending release survive reboot and failed setup. The installed `grandma-update` command resumed a fixture across a real VM reboot without downloading its package again; a same-boot retry correctly returned 75. The fixture used a setup shim to request that reboot, not a native package change. The final existing-VM installation/update run passed all 154 checks, including personal-setting preservation. Unit checks cover retry, concurrent operations, completed-state recovery and explicit discard of a failed package. Test version markers are restored after the fixture so they cannot hide the first real release.

A manual main-only workflow prepares a release draft, archive, source revision and checksum. Its YAML and shell syntax and the local package builder were checked; the GitHub workflow was not run and nothing was published. The public latest-release lookup currently reports no stable release. Feature implementation for this round is complete; physical hardware, the applicable release-acceptance checks and installation/update from the first published GitHub asset remain pending. See [Updates](UPDATES.md) and [release preparation](RELEASING.md).
