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
| Win11 icons | Yeyushengfan258 and AUTHORS in the package | https://store.kde.org/p/1407137 | See COPYING and AUTHORS in the downloaded package |

Windows wallpaper dependencies are omitted so personal wallpaper is preserved. AeroThemePlasma/AeroShell is not installed. The chat icon in `assets/chat.svg` is original project artwork under MIT.

## Internet launcher icon

At the maintainer's request, the Internet launcher uses the Chromium project icon while continuing to launch Brave. The source revision and SHA-256 are pinned in `data/internet-icon.json`. The icon is downloaded from Chromium upstream under its [BSD license](https://chromium.googlesource.com/chromium/src/+/main/LICENSE); it is not bundled here. This does not indicate Chromium is installed or that Chromium endorses this project. The start-menu icon in `assets/start.svg` is original MIT artwork.

The installed Se7en Aero Plasma Style is locally adjusted to use 96% opacity on the popup background backing layer. The original SVG is retained beside it as `.before-grandma`; theme assets remain outside this repository.
