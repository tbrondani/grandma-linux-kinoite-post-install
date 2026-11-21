# Help and first steps

The desktop has **Help** and **User manual** shortcuts. Help offers three choices: How to use, Remote support, and Support information. The manual works offline. It has a task list, short procedures and an English/PT-BR language switch. Closing a page returns to the task list. Remote support uses the existing manual RustDesk launcher.

Support information shows system version, CPU, RAM, free disk space, app versions and backup status. It does not collect user names, host names, IP addresses, passwords or the recovery key. Nothing is uploaded.

**System → Updates** opens Discover's Updates page. The user reviews and starts updates. This shortcut does not enable unattended updates or force a restart.

All tools use KDE dialogs and system Python. They add no background application. The backup runs through a monthly systemd user timer; see [Backup](BACKUP.md).

The manual source is `data/guides/manual.en.json` and `manual.pt-BR.json`. The desktop shortcut reuses `grandma-guide.desktop`; it does not add a duplicate shortcut. English procedures follow ASD-STE100 principles: imperative instructions, one action per step, consistent interface names and at most 20 words per step. Application names and key names are technical terms. PT-BR is a plain-language adaptation. This is not a full approved-vocabulary compliance audit. The writing reference is [ASD-STE100, Issue 9](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf).
