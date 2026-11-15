# Development status

The initial installation path has been exercised on Fedora Kinoite 45 with Plasma 6.8.3 and Wayland in the development VM. This is not a release qualification or a physical hardware test.

## Implemented and checked

- English and Brazilian Portuguese setup messages and localized launchers.
- Git-free archive bootstrap, tested locally with download fixtures.
- Kinoite, Plasma 6, Wayland, and architecture checks.
- Batched installation of restic and Vim, with a reboot boundary.
- Curated apps and games; existing native and Flatpak apps are preserved.
- User-scope Flathub with app availability checks.
- Selected desktop shortcuts, WhatsApp launcher, and explicit Flatpak icon paths.
- Task folders in the application menu and default file associations.
- Double-click behavior, disabled middle-click paste, and Flameshot auto-save configuration.
- Se7en Aero 3.1 with pinned KDE Store components, bottom panel, and column layout. The user wallpaper is preserved.
- Guest validation, application startup probes, repeat-run checks, and JSON reports.
- Test VM SSH and Plasma Login Manager auto-login, checked after reboot.

## Latest development VM results

85 automated checks passed after installing from the restored base. All 26 application startup probes passed with Se7en Aero. A KWallet prompt required user interaction during the run; this is not a fully unattended first-use acceptance test. Repeating setup preserved generated files, app inventory, and OSTree deployments. These probes do not prove every application's features work.

## Pending before v0.1.0

- Recreate a VM from installation media to qualify provisioning. The latest setup run started from the saved clean Fedora base, with SSH and automatic login prepared first.
- Physical hardware, camera, microphone, audio, suspend, and networking tests.
- Visual review of the menu, icons, panel, wallpaper, screenshots, and desktop behavior.
- First-use KWallet prompts under test VM auto-login. Keep credential storage enabled; startup probes do not prove a prompt-free first launch.
- Brave feature reduction and end-to-end web app tests.
- Backup repository setup, encryption, monthly timer, retention, and safe restore.
- RustDesk manual-only access and confirmed shutdown behavior on Wayland.
- Local AI deployment and resource tests.
- Offline dictionary and map data preparation and validation.
- Complete upstream license inventory and translated contributor guides.
- Windows 10 preset and final acceptance of the visual direction.

Se7en Aero is installed directly from KDE Store. `data/themes.json` pins the five reviewed downloads by SHA-256. Theme archives and assets are not bundled in this repository. Upstream layout scripts are not executed and wallpaper dependencies are not installed. The chat launcher uses an original MIT icon.

References: [Flatpak commands](https://docs.flatpak.org/en/latest/flatpak-command-reference.html), [rpm-ostree](https://github.com/coreos/rpm-ostree/blob/main/docs/administrator-handbook.md), [AeroThemePlasma installation](https://github.com/aeroshell-desktop/aerothemeplasma/blob/Plasma/6.8/INSTALL.md), [Plasma Login Manager](https://github.com/KDE/plasma-login-manager).
