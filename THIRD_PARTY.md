# Upstream projects

Grandma Linux integrates and configures other projects. Their authors retain credit for their work.

The list below describes planned integrations. No third-party software or assets are bundled in this repository.

| Project | Planned use | Source and support information |
| --- | --- | --- |
| Fedora Kinoite | Base operating system | https://fedoraproject.org/atomic-desktops/kinoite/ |
| KDE | Desktop, tools, and games | https://kde.org/ |
| Flatpak / Flathub | Application delivery | https://flatpak.org/ / https://flathub.org/ |
| Brave / Firefox | Web browsing | https://brave.com/ / https://www.mozilla.org/firefox/ |
| VLC | Audio and video | https://www.videolan.org/vlc/ |
| ONLYOFFICE | Documents | https://www.onlyoffice.com/desktop.aspx |
| LocalSend | Local file transfer | https://localsend.org/ |
| Mission Center | Task manager | https://missioncenter.io/ |
| restic | Backups | https://restic.net/ |
| RustDesk | Remote support candidate | https://rustdesk.com/ |
| Omnidict | Offline dictionary candidate | https://flathub.org/apps/com.ktechpit.omnidict |
| Organic Maps | Offline maps candidate | https://organicmaps.app/ |
| Open WebUI / Qwen | Local AI candidates | https://github.com/open-webui/open-webui / https://github.com/QwenLM/Qwen3 |

To donate, visit the relevant project's official site and check its support options.

Before adding an integration, verify its source, license, version, and installation method. Record modifications and redistribution here. Review theme assets and offline data licenses separately. Do not bundle assets without permission under their license.

## Desktop theme

The installer downloads these packages from KDE Store; this repository does not bundle their assets. `data/themes.json` records the exact archive names and SHA-256 hashes. No upstream shell or layout script is executed. The project does not claim ownership of the artwork.

| Component | Author / attribution | Source | License information |
| --- | --- | --- | --- |
| Se7en Aero 3.1 | LinLinXZA and credited contributors | https://store.kde.org/p/1407086 | GPL-2.0-or-later in package metadata |
| Se7en Aero Aurorae 0.3 | Infinality / upstream package | https://store.kde.org/p/1406638 | GPL_V2 in package metadata |
| Se7en Aero Plasma Style 0.9.4.8 | Upstream theme contributors | https://store.kde.org/p/1407084 | Complete asset license review pending before redistribution |
| Win7OS colors | Yeyushengfan258 | https://store.kde.org/p/2143603 | Complete asset license review pending before redistribution |
| 7 Icons (Win2-7) 1.0 | Elbullazul / B00merang-Artwork; original Win2-7 contributors | https://store.kde.org/p/1354234 | Upstream package has no complete license statement; full asset review remains required before redistribution |

Windows wallpaper dependencies are omitted so personal wallpaper is preserved. AeroThemePlasma/AeroShell is not installed. The chat icon in `assets/chat.svg` is original project artwork under MIT.

## Internet launcher icon

At the maintainer's request, the Internet launcher uses the Chromium project icon while continuing to launch Brave. The source revision and SHA-256 are pinned in `data/internet-icon.json`. The icon is downloaded from Chromium upstream under its [BSD license](https://chromium.googlesource.com/chromium/src/+/main/LICENSE); it is not bundled here. This does not indicate Chromium is installed or that Chromium endorses this project. The start-menu icon in `assets/start.svg` is original MIT artwork.

The installed Se7en Aero Plasma Style is locally adjusted to use 96% opacity on the popup background backing layer. The original SVG is retained beside it as `.before-grandma`; theme assets remain outside this repository.

## Dictionary data

`data/dictionaries.json` pins eight FreeDict bundles from the Omnidict catalogue and two WikDict StarDict archives. Each installed database includes its license and attribution; `SOURCE.json` retains the source URL and checksum. Portuguese–Italian and Spanish–Portuguese WikDict data are converted into Omnidict's documented SQLite bundle schema. Converted WikDict data remain CC-BY-SA-4.0; FreeDict packages retain their declared licenses. No dictionary data is bundled in this repository.

## Organic Maps data

`scripts/maps.py` is a project implementation of the catalogue-based download approach documented by Organic Maps' `tools/python/mwm_downloader.py` (https://github.com/organicmaps/organicmaps/blob/master/tools/python/mwm_downloader.py). No upstream Python code is bundled. It uses the installed application's catalogue and official HTTPS mirror discovery service. Downloaded `.mwm` data remain subject to Organic Maps' [data license and attribution](https://github.com/organicmaps/organicmaps/blob/master/DATA_LICENSE.txt), including OpenStreetMap contributors. Map data are not bundled in this repository.

## Offline sentence translator

Argos Translate 1.11.0 and Argos Translate GUI 1.6.5 are MIT-licensed upstream packages (https://github.com/argosopentech/argos-translate and https://github.com/argosopentech/argos-translate-gui). `scripts/translator-ui.py` adapts the upstream GUI with English/PT-BR labels, explicit translation and exception handling. It does not copy or vendor upstream application code.

The isolated environment uses uv 0.13.8 (MIT/Apache-2.0), CPython 3.12.16 and pinned Python dependencies; their licenses remain installed with each distribution. CPU-only PyTorch is used. `data/translation-models.json` pins Argos OPUS model downloads, retaining upstream README and attribution inside each installed package. Model/data licenses are separate from this repository's MIT license. MiniSBD (AGPL-3.0, https://github.com/LibreTranslate/MiniSBD) and six pinned sentence models provide offline sentence splitting. No upstream packages or model binaries are bundled in this repository. Complete dependency and model license review remains a release requirement.

Organic Maps 2026.11 uses `countries.json` and a nine-byte BLAKE3 digest. The downloader also accepts the older `countries.txt`/SHA-1 catalogue. The native `b3sum` package verifies modern maps using the upstream catalogue format (https://github.com/organicmaps/organicmaps/blob/master/tools/python/post_generation/hierarchy_to_countries.py). No upstream hashing implementation is vendored.

The pinned 7 Icons package replaces the Win11 download for new setup runs. Its `Windows-7-1.0/index.theme` inherits `breeze,hicolor` locally, because the original Gnome/Windows fallback themes are absent on Kinoite. Existing icon themes are retained. These assets are downloaded directly, not redistributed in this MIT repository.

## Reading font

Atkinson Hyperlegible Next is by the Atkinson Hyperlegible Next Project Authors / Braille Institute, under SIL Open Font License 1.1. `data/reading-fonts.json` pins four unchanged TTF files and OFL.txt from [upstream revision 7925f50](https://github.com/googlefonts/atkinson-hyperlegible-next/tree/7925f50f649b3813257faf2f4c0b381011f434f1). The font and license are installed together in the user's font directory. Font binaries are not bundled in this repository.

## Release automation

[Release Please Action](https://github.com/googleapis/release-please-action) and [Release Please](https://github.com/googleapis/release-please) are Apache-2.0 projects by Google. The workflow references the action at a pinned commit; upstream code is not bundled here.
