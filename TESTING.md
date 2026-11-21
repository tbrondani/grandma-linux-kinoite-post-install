# Testing and releases

Run `bash tests/check.sh` for local checks. These checks use mocks and do not prove that installation works on Kinoite. The checks below define the release target.

## Installation

1. Start with a clean Fedora Kinoite VM. Record Fedora, Plasma, and session versions.
2. Follow only the repository documentation. Reboot and resume when requested.
3. Run setup again. Check that apps, shortcuts, remotes, and timers are not duplicated and personal files are preserved.

If installation needs an undocumented manual fix, fix the project and repeat the test.

## Desktop and hardware

Check both English and Brazilian Portuguese. Open each installed app and check task names, search, file associations, and theme persistence after reboot.

On physical hardware, test networking, audio, microphone, camera, suspend, USB, and updates. Test backup and restore to a separate folder. Validate offline data, localhost-only AI, and remote support stopping when closed before claiming those features work.

## Release

1. Merge reviewed changes through a pull request. Record test results and known limits.
2. Choose a version such as `v0.1.0` and prepare release notes.
3. Tag the tested main commit and publish a GitHub release.

Do not publish a working-installation claim until the clean VM and physical hardware checks pass. Automated release publishing can be added once these checks are implemented.

## Guest report

In a PT-BR desktop session inside the test VM, run:

```sh
python3 tests/validate.py > validation-report.json
```

Exit status 1 means at least one required check failed. The report checks installed apps, localized launchers, and desktop shortcuts. It does not prove that app windows work or that remote access is secure. Review those manually.

The supplied host start script currently cannot run inside the coding environment: sudo is blocked by the no-new-privileges setting. A host-side start or an accessible libvirt connection is needed for real VM tests.

## Start, install, and validate

On the host, with the test VM already installed:

```sh
bash scripts/vm/start-test.sh
```

The default guest user is `maria` (lowercase). This account must already exist; the runner does not create it. SSH accepts a key or asks for the guest password. Enable sshd in the VM and log into its KDE Wayland desktop first. To enable SSH once, run `sudo systemctl enable --now sshd` inside the VM. If the firewall blocks SSH, allow the SSH service in the active guest firewall zone. Override `VM_USER` if the installed account has another name. If address discovery fails, set `VM_HOST` to the guest IP. No Git is needed in the guest.

The runner starts the existing VM, sends the local working tree, runs setup, reboots for pending deployments, and collects `test-results/validation-report.json`. After reboot, log into KDE again if auto-login is not configured, then rerun the command if it stopped. Authorization prompts for rpm-ostree may appear in the guest desktop. The runner never deletes the VM or its disk.

Guest installation, reboot/resume, and validation have been exercised on the development VM; a complete fresh ISO provisioning qualification remains pending. It installs only the implemented features listed in docs/STATUS.md. RustDesk and other pending integrations will not become available just by running it.

## Create the test VM automatically

`bash start-knoite.sh` from the workspace now creates the VM if absent. It needs `virt-install`, libvirt/KVM, SSH tools, OpenSSL, and a Fedora Kinoite installer ISO on the host. The local default ISO is `/home/hackerman/Downloads/codebase/Fedora-Kinoite-Installer-45-1.4.x86_64.iso`. Override `ISO_PATH` on other hosts. `FEDORA_VERSION` defaults to `45` and selects the matching OSTree branch. The host default libvirt network must be active.

The new disposable VM has 8 GB RAM, 4 vCPUs, and a 40 GB disk. Kickstart installs Fedora Kinoite 45 from the OSTree repository embedded in the installer ISO, creates `maria`, enables SSH with a generated test key, selects PT-BR, and enables desktop auto-login. No reusable user password is set. Host sudo may prompt during VM creation. Installation requires internet access and can take up to 30 minutes before SSH is ready.

The private key and generated Kickstart stay in ignored `.vm-state/`. Test-only sudo rules permit package layering and reboot; these settings are not part of the end-user installer. Existing VMs are never erased or retroactively provisioned.

This provisioning path remains unverified on real libvirt. References: [Kickstart](https://pykickstart.readthedocs.io/en/latest/kickstart-docs.html) and [Fedora Kinoite OSTree reference](https://fedoramagazine.org/how-to-rebase-to-fedora-linux-44-on-silverblue/).

The creation script copies the ISO to `/var/lib/libvirt/images/grandma-media/` before starting QEMU and restores its SELinux context when available. This avoids granting QEMU access to the maintainer's home directory. The copy uses additional disk space.

The installer uses `file:///ostree/repo`, following Fedora Atomic installer media conventions, rather than pulling the initial deployment from a network repository. `--nogpg` applies to this local media import; verify the original ISO against Fedora's signed checksums before use. Network update verification is a separate release check.

## Clean baseline for each run

After completing the initial KDE setup and before running the Grandma Linux installer, save the baseline on the host:

```sh
bash scripts/vm/baseline.sh save
```

The default VM is `fedora-kinoite-test-v2`. The script requests a clean shutdown and refuses to copy a running disk. It stores a standalone qcow2 disk and reference domain XML under `/var/lib/libvirt/images/grandma-baselines/`. It never replaces an existing baseline. This is a disk baseline, not a snapshot of RAM or UEFI variables.

Subsequent starts restore this baseline by default, discarding the previous guest test changes. Reports in host `test-results/` remain. Use `FRESH=0 bash scripts/vm/start-test.sh` to resume a test without restoring. For a real clean-run claim, ensure the saved base predates all project installation changes.

## SSH prerequisite before saving a clean base

In the guest, enable and verify SSH before running any project installation:

```sh
sudo systemctl enable --now sshd
sudo firewall-cmd --add-service=ssh
sudo firewall-cmd --permanent --add-service=ssh
systemctl is-active sshd
```

From the host, verify SSH access with the test key before saving the baseline. Stop the host test runner first so it cannot install project packages while preparing the base. A running SSH service is expected; stop the host runner, not sshd. If the runner already installed anything, restore the old clean base with `baseline.sh restore`, start the VM directly through virt-manager, enable SSH, and save a replacement base. Do not run the install runner between restoring and saving.

To replace the baseline, use `baseline.sh update`. It shuts down the VM cleanly and retains the previous baseline as `base.previous.qcow2`. Only use this after confirming that the guest contains Fedora plus test prerequisites and no Grandma Linux installation changes.

Guest test files are stored in `~/.local/state/grandma-linux-tests/`, which survives reboots. After reconnecting through SSH, the guest runner also waits for the KDE Wayland session before resuming setup.

## Development VM checks

Run these inside the logged-in test VM, from the repository folder:

```sh
python3 tests/validate.py > validation-report.json
python3 tests/smoke-apps.py
python3 tests/repeat-run.py
```

The startup probe opens and closes apps it starts. Existing open apps are left alone. This checks launch failures, not rendering or interaction. The repeat-run check compares generated files, installed app inventory, and deployment checksums before and after setup. It runs the setup again.

The November 15 Se7en Aero run passed 85 checks from the restored base and repeat-run checks, including wallpaper preservation. Application startup is tested separately. Reports are in ignored host `test-results/`. Initial provisioning required corrections; this does not establish a pristine end-to-end install or physical hardware support.

Kinoite 45 uses Plasma Login Manager. Test provisioning configures `/etc/plasmalogin.conf`; SDDM configuration alone does not enable its auto-login. This setting is for the disposable test VM, not a requirement for an end-user machine.

A startup process can remain alive while displaying a KWallet prompt. Record credential dialogs separately; do not count startup success as a prompt-free end-user experience. The test VM uses auto-login, which does not provide the login password to kwallet-pam. Do not disable credential storage to make the startup probe pass.

Run `python3 tests/remote-support.py` in the guest to check the supported launcher. It opens only RustDesk, minimizes its own window, then closes it through KWin. It checks that minimizing preserves the session and closing stops the sandbox. It does not inject input or validate a real incoming connection. Close any existing support session first.

Offline translator checks (inside the VM, with no network):

```sh
unshare -Urn ~/.local/share/grandma-linux/translator/venv/bin/python tests/offline-translator.py
unshare -Urn ~/.local/share/grandma-linux/translator/venv/bin/python tests/translator-ui.py
```

The GUI test uses an offscreen Qt platform and does not inject desktop input. Review translation quality and the actual UI manually. See [size measurement](docs/INSTALLATION-SIZE.md) for before/after inventory commands.

`python3 tests/test_backup.py` needs restic. It creates temporary repositories and checks actual data recovery, repeat setup, retention isolation, missing storage, init failure, concurrent operations and a simulated reinstall. It does not modify the user's backup. Host checks skip these tests if restic is absent; run them in the VM.

For a clean test VM that does not log into Maria automatically, run inside the guest before setup:

```sh
sudo python3 scripts/vm/configure-login.py --user maria
```

The helper configures Plasma Login Manager and SDDM, and enables system SSH. Reboot and verify the Wayland session before saving a clean baseline. Do not update a baseline from a VM after the project installer has run.

Deployment logs are saved under `test-results/` and remain outside Git:

- `deploy-<UTC timestamp>-<id>.log`: host and guest console output.
- The matching `.json`: host exit code, phase, VM and guest work directory.
- `deploy-...-guest-setup.log`: guest setup output, retained across the reboot stage.
- `deploy-...-guest-execution.json`: separate setup and validation exit codes.
- `validation-report.json`: individual acceptance checks.

The runner copies guest logs even when setup fails before validation. A run that started before logging was added cannot provide its earlier console output retroactively. `python3 tests/test_vm_runner.py` verifies logging, failure propagation and the reboot boundary without changing a VM.

Restoring the plain-layout test VM now also prepares its login configuration in the offline working copy with guestfish. The saved baseline is read-only during this operation. The host requires `guestfish` (libguestfs tools). The helper accepts only `.grandma-restore` images, checks the OSTree deployment layout, and labels the added configuration files for SELinux. Unsupported disk layouts stop before the live disk is replaced.
