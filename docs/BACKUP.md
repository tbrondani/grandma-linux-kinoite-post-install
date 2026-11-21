# Local file backup

Setup creates the first copy and enables a monthly user timer. It copies Desktop, Documents, Downloads and Pictures. It keeps 12 monthly and 3 yearly versions, plus the latest copy. The computer must be on with the user session active. A missed scheduled run is attempted after the user session starts again.

- **Utilities → Backup:** make a copy now, check the last success, or open the saved backup folder.
- **Utilities → Recover Files:** choose a version and a destination. Files go into a new folder; current files are preserved.
- To open a copy from another installation, select **Open a saved backup folder**. This does not change the current automatic backup.

The default bundle is `~/.local/share/grandma-linux/backups/local`. To move it later, copy this entire folder, including `repository`, `grandma-backup.json`, `recovery-key.txt` and `RECOVERY.txt`. Restic encrypts the repository. The recovery key is included for local recovery; anyone with both can read the backup. Keep the bundle private.

Preserve this folder during reinstall, or copy it elsewhere first. Formatting the disk also erases a backup on that disk. This is a personal-file backup, not a system image. After reinstall, run Grandma Linux setup, open Recover Files and select the preserved bundle.

Failures retain the previous backup. Retention applies only to snapshots tagged for this integration. Files from unrelated backup sets are not removed. Restore verifies recovered data and never replaces live files.
