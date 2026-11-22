# Updates

Open **Updates** on the desktop or in **System**.

1. Select **Grandma Linux setup and manual**.
2. Review the installed and offered versions. Confirm the update.
3. Keep the computer on until the progress window closes.
4. If asked, restart and select the same update option to finish.

The verified package is saved across restarts. Wallpaper, reading preferences, existing launchers and backup settings are preserved. New applications get launchers; removed desktop shortcuts are not recreated. New theme assets are installed without selecting a different appearance. If an update fails, select **View the last project update log**, then retry.

Select **System and applications** to update Fedora and Flatpaks with Discover. Translation models, map catalogues and curated defaults change through project releases; this is separate from Discover's package updates.

For terminal maintenance, no Git or sudo is needed:

```sh
~/.local/bin/grandma-update --check
~/.local/bin/grandma-update --apply --lang=en
```

The second command asks for confirmation. After a requested restart, run it again. Exit code 75 means restart is required; 1 means failure. The update may request system authorization for new native packages. It never restarts the computer automatically.

Only stable releases from the project repository are offered. The archive must match GitHub's asset SHA256 digest. Until a stable release is published with the update asset, the tool reports that no version is available. It does not install unpublished branches.

If a saved update repeatedly fails, select **Start the project update again**. Confirm to discard its cached package, then check the latest release again. Installed applications and settings are kept.

Updates reuse `~/.config/grandma-linux/profile.yaml`. To change component selection, preview and apply it with **Installer**, or pass `--config profile.yaml` to `grandma-update --apply`. Profile changes are reported and retained across a required reboot. See [Profiles](PROFILES.md).
