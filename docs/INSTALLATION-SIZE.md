# Installation size

Development VM measurement, 2026-11-16. Use decimal GB below. These values are not hardware requirements.

| Component | Download | Disk use |
|---|---:|---:|
| User Flatpak repository, apps and shared runtimes | See per-ref estimates | 7.36 GB allocated |
| Argos, isolated Python and ten translation models | Models: 880 MB; Python dependencies extra | 2.67 GB allocated |
| Portugal maps | 451 MB | 451 MB of map files |
| Ten dictionaries | 13.5 MB | 45.6 MB of database files |
| Theme archives | 14.6 MB | See detailed inventory |
| Fastfetch + yyjson (added after the inventory) | 0.845 MB reported by rpm-ostree | 2.413 MB of package files |
| b3sum (added 2026-11-21) | 0.437 MB reported by rpm-ostree | 1.062 MB of package files |
| Help and backup helpers (added after the inventory) | Included in the project archive | 0.066 MB allocated |

The 2026-11-21 deployment uses map catalogue 261110; the table above records the earlier catalogue.

The self-contained HTML manual is about 32 kB. It uses the existing browser and adds no production runtime, server or frontend dependency. Browser automation tools are test-only and excluded from setup.

The first VM backup used 1.16 MB for 13 small files (84 kB of source data). Backup storage depends on personal files and retained versions; it is not included in the earlier directory total.

Map and dictionary data are inside app data directories. Do not add them to the directory totals again. Argos model archives are removed after installation.

The monitored directories occupy **15.79 GB**, including **4.94 GB of system Flatpaks already present in Fedora**. This is a current inventory, not the project's additional disk cost. Native packages, other OS files and personal data outside these directories are not included.

[Detailed inventory](measurements/2026-11-16.md) lists each app, shared runtime, map, dictionary, translation model and native package. Flatpak download estimates total 6.14 GB for 44 available refs; 15 refs have no estimate. These are rounded remote sizes, not captured traffic. Locale extensions report full remote sizes even when only selected languages are installed.

For a clean before/after measurement, run in the VM:

```sh
python3 scripts/installation-size.py --output before.json
# Run setup, including its reboot stage, then:
python3 scripts/installation-size.py --before before.json --output after.json --markdown sizes.md
```

Keep measurements outside Git unless reviewed for publication. A filesystem delta also includes unrelated changes; use the same clean VM and avoid other work during measurement. Exact setup traffic and total additional disk cost remain pending a clean baseline run.
