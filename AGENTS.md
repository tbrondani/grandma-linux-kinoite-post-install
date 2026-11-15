# Working on Grandma Linux

- Keep changes small and useful to non-technical users.
- Use English for code, commits, and primary documentation. Support Brazilian Portuguese from the start; do not add European Portuguese.
- Follow ASD-STE100 principles for English instructions. Use Brazilian plain language for translations. Keep commands identical across languages.
- Keep documentation short. Link to details instead of repeating them.
- Keep the MIT license. Credit upstream projects in THIRD_PARTY.md.
- Never push; the maintainer handles pushes with their SSH key. Keep the initial implementation uncommitted until it is ready for one consolidated commit.
- Work on a branch. All changes to main must go through a pull request.
- Publish a versioned release after the release checks pass. Never claim untested support.
- Keep private handoff files outside this repository. Do not copy them into tracked files.
- Prefer Flatpak for graphical apps and rpm-ostree for Kinoite system tools. No Snap or AppImage in the official path.
- Setup must be safe to repeat. Preserve personal files and existing working apps.
- Use localized user directories, not hard-coded folder names.
- Never enable unattended remote access. Local AI must use localhost and must not control the system.
- Verify installation in a clean VM and on physical hardware before release. See TESTING.md.

- VM tests may create the named test VM if absent. Never recreate or delete an existing VM implicitly.

- VM clean bases must have working SSH, the test key, and a logged-in PT-BR desktop verified before capture. Never capture a clean base after running the project installer.
