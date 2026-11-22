# Installation profiles

No file is required. A new installation uses the current complete app selection and the current English/PT-BR session language. Existing installations reuse saved preferences. AI stays off until implemented.

Open **Installer** on the desktop, or run the existing curl installer. The interactive menu offers install/repair, reconfigure and project update. You can reuse a profile, choose an existing YAML, or generate `grandma-profile.yaml` in the current folder. Template generation stops; edit it before rerunning. Automated calls without a terminal use saved/default preferences.

```sh
~/.local/bin/grandma-install --template grandma-profile.yaml
~/.local/bin/grandma-install --config grandma-profile.yaml --dry-run
~/.local/bin/grandma-install --config grandma-profile.yaml --yes
```

Before the first installation, replace `~/.local/bin/grandma-install` with `bash setup.sh` in a downloaded checkout, or pass the same options after `bash -s --` in the documented curl command.

A small custom profile can contain only:

```yaml
schema_version: 1
language: pt-BR
features:
  games: false
  translator: false
  remote_support: false
  ai: false
```

The omitted settings keep saved preferences, or defaults on a new account. Keep personal profiles outside the Git repository. The generated root template is ignored by Git. The complete example is [profile.example.yaml](../data/profile.example.yaml). Use two-space indentation and literal `true`/`false`. Profiles support nested mappings and strings, integers, booleans and null. YAML sequences, aliases, tags and multiline values are not supported. No YAML package is downloaded to read a profile.

| Feature | Managed component |
| --- | --- |
| accessibility | Reading font and presets; initial night-light defaults |
| theme | Pinned Windows-style theme/icon assets; initial appearance |
| offline_maps | Organic Maps and the selected Portugal data bundle |
| dictionaries | Omnidict and ten offline dictionaries |
| translator | Argos sentence translator and its models |
| games | Curated games |
| remote_support | RustDesk and the temporary-password support launcher |
| backup | Local backup setup and monthly timer |
| ai | Reserved; true fails before installation until implemented |

False does not uninstall apps, erase data or undo the current appearance. Disabling backup stops only the project's own timer; the repository and recovery key remain. Re-enabling backup preserves an existing backup destination and timer settings. Reconfiguration and updates do not force a different wallpaper, theme or reading preset.

Use `grandma-install --list-apps` for selectable IDs. `applications` accepts boolean overrides; the core Brave browser and Dolphin stay enabled. Feature-owned apps require their corresponding feature. For example, turn off `features.offline_maps` instead of disabling only Organic Maps. A template's `applications: {}` restores default app overrides.

`environment` contains non-secret string values for new user sessions. Installer paths, identity, shell/Python/loader controls, locale overrides and secret-variable names are rejected. Use `language` for locale selection. Missing English/Portuguese locale data are installed through rpm-ostree and may require a reboot. To remove an environment key in a partial custom file, set its value to null. An empty `environment: {}` clears the project's environment additions. Other user environment files are preserved.

## Reinstall and history

Preferences live in `~/.config/grandma-linux/profile.yaml`. Copy this file to another computer, or retain it on a preserved home filesystem. Do not use the observed installation JSON as an input profile. The observed state in `~/.local/state/grandma-linux/installation.json` records the actual account/home, home mount and curated app availability. It is not a filesystem backup.

```sh
~/.local/bin/grandma-install --list-snapshots
~/.local/bin/grandma-install --from-snapshot SNAPSHOT_ID --dry-run
~/.local/bin/grandma-install --from-snapshot SNAPSHOT_ID --yes
```

Private dated snapshots record desired settings, the previous applied profile and complete/failed/reboot-required status. Reusing a snapshot selects its preferences; it does not roll back files or remove newer apps. Preferences are saved before a package reboot, so the original custom input file is no longer required. Failed runs keep the previous applied state. Project updates reuse the profile automatically; a new optional feature stays off in an older saved profile until selected.

`system.username` and `system.home` are assertions about the existing desktop account. `storage.mount_points` maps names such as `home` to already mounted paths such as `/var/home`. Unmet assertions stop the installer. It does not create accounts, move home directories, edit fstab or partition disks. Prepare a separate home filesystem with the Fedora installer and keep an off-device backup.

## New test VMs

```sh
bash scripts/vm/create.sh --config grandma-profile.yaml
```

Only new disposable VMs use `vm.username` and `vm.autologin`; existing domains are never changed by these keys. The old defaults remain Test user with auto-login and a PT-BR session when no profile is supplied. `VM_CONFIG=...` can also be used by the host start script; use a new VM name for new provisioning. For a profile without auto-login, use `FRESH=0` and log in manually before desktop tests. Guest component selection uses `TEST_PROFILE=...`; it does not change the existing VM account.

Only Fedora Kinoite x86_64 with Plasma 6/Wayland is supported. The profile/manifest format can be reused by future backends, but this version installs no Arch, DNF or Homebrew backend.
