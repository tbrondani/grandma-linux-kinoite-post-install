# Help and first steps

The desktop has **Help** and **User manual** shortcuts. Help offers three choices: How to use, Remote support, and Support information. The manual opens as an offline book with a chapter index, previous/next pages, favorites, English/PT-BR selection, light/dark themes and text enlargement. Reading preferences and favorites remain in that browser profile; clearing its local data removes them. Remote support uses the existing manual RustDesk launcher.

Support information shows system version, CPU, RAM, free disk space, app versions and backup status. It does not collect user names, host names, IP addresses, passwords or the recovery key. Nothing is uploaded.

**System → Updates** opens Discover's Updates page. The user reviews and starts updates. This shortcut does not enable unattended updates or force a restart.

Backup and support use KDE dialogs and system Python. The manual uses the existing Brave in an app window, with the default browser as a fallback. It adds no server or background service. The backup runs through a monthly systemd user timer; see [Backup](BACKUP.md).

The manual content is `data/guides/manual.en.json` and `manual.pt-BR.json`. Its HTML/CSS/JavaScript sources are in `data/manual`. `scripts/manual.py` generates one self-contained `.grandma-linux-manual.html` file in the localized desktop folder, which the existing Brave Flatpak can already read. No new filesystem permissions, external fonts, CDN or internet connection are required. The desktop shortcut reuses `grandma-guide.desktop`; it does not add a duplicate shortcut. English procedures follow ASD-STE100 principles: imperative instructions, one action per step, consistent interface names and at most 20 words per step. Application names and key names are technical terms. PT-BR is a plain-language adaptation. This is not a full approved-vocabulary compliance audit. The writing reference is [ASD-STE100, Issue 9](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf).


For larger text, open **System → Reading comfort**. Choose 12 or 14 pt, or restore the previous settings. See [Reading comfort](ACCESSIBILITY.md).

Open **Updates** on the desktop or in **System**. Choose **System and applications** for Discover, or **Grandma Linux setup and manual** for a stable project release. The window shows the installed version, progress and the last update log. If asked, restart and select the same project update to finish. See [Updates](UPDATES.md).
