# Grandma Linux

[Português (Brasil)](docs/README.pt-BR.md)

A post-install setup project for Fedora Kinoite and KDE Plasma. It aims to make everyday tasks easy to find, with familiar desktop layouts and clear application names.

**Status:** early development. The initial setup has been tested in a Fedora Kinoite 45 VM. Physical hardware and release acceptance tests are still pending.

## Preview

```sh
./setup.sh --dry-run --lang=en
```

The preview makes no changes. For development testing on a disposable Kinoite VM, run `./setup.sh --lang=en` as your desktop user. Reboot and run it again if requested. It installs apps and games and may request system authorization.

## Target platform

Fedora Kinoite, KDE Plasma 6, Wayland, and x86_64. Supported Fedora versions will be listed here after testing.

## Planned features

- English and Brazilian Portuguese.
- Task names such as Photos, Internet, and Remote Support.
- Curated apps, optional familiar themes, and encrypted backups.
- Offline dictionaries and maps.

## Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for changes and bug reports, and [SECURITY.md](SECURITY.md) for security reports.

This is a hobby project. If you want to donate, support the [upstream projects](THIRD_PARTY.md) that make it possible.

Licensed under [MIT](LICENSE).

## Install without Git

After these files are published on main:

```sh
curl -fsSL https://raw.githubusercontent.com/tbrondani/grandma-linux-kinoite-post-install/main/install.sh | bash -s -- --dry-run --lang=en
```

Remove `--dry-run` to install in a test VM. The installer downloads an archive and does not require Git. After a requested reboot, run the same command again. Do not use on your main machine yet.

To use a published version, replace `main` in the URL with its tag and pass `GRANDMA_REF=vX.Y.Z` to Bash. No tested release exists yet.

After setup, open **Help** or **User manual** on the desktop. See [local backup and recovery](docs/BACKUP.md).

## Updates

Open **Updates** on the desktop or in **System**. Choose **Grandma Linux setup and manual** for a stable project release, or **System and applications** for Discover. See [Updates](docs/UPDATES.md) and [release preparation](docs/RELEASING.md).

## Installation profiles

Open **Installer** to reuse the current profile or choose a YAML file. Preview with `./setup.sh --config profile.yaml --dry-run`. Preferences, applied state and private history are separate; disabled features retain existing data. See [profiles](docs/PROFILES.md).
