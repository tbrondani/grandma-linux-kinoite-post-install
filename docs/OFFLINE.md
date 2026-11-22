# Offline maps and dictionaries

Setup downloads Portugal maps automatically. It uses the installed Organic Maps catalogue and verifies each file's size and integrity hash (SHA-1 or BLAKE3). Restart Maps after setup. Open Portugal and disconnect the network to check the map.

For another region, run `python3 scripts/maps.py --region Brazil_Bahia` from the project folder. Use the exact region ID from the app catalogue. Brazil is not downloaded by default.

Setup also installs Portuguese dictionaries for English, Spanish, French, German and Italian, in both directions. Open Dictionary and select a dictionary. These are word dictionaries, not full-text translators.
