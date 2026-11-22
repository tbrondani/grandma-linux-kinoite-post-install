# Releases

[Release Please](https://github.com/googleapis/release-please-action) collects changes merged into main in a release pull request. It updates `VERSION` and `CHANGELOG.md`. The first release is `v0.1.0`.

1. Merge feature and fix PRs into main. Use conventional commit titles such as `feat: add a tool` or `fix: resume an update`. Use squash merge to keep that title as the commit message.
2. Review and merge the release PR when ready to publish.
3. The workflow checks the tagged source, builds the installer archive and checksum, uploads both, and publishes the release. No manual workflow run is needed.
4. Restore the clean test VM baseline and test installation through curl at the published tag. Test project updates before using them on a target PC.

Repository setup: in **Settings → Actions → General → Workflow permissions**, enable **Allow GitHub Actions to create and approve pull requests**. The workflow uses the repository's `GITHUB_TOKEN`; it needs no personal token. Bot-created PRs do not trigger normal PR workflows with this token. The release workflow runs checks before automation and again before publishing.

If packaging or upload fails, the release stays a draft. Inspect the failed run. Upload the missing verified archive/checksum from the same tagged commit, then publish the draft. Never reuse a published version for different content. Do not merge another release PR until that draft is resolved.

Assets must be named `grandma-linux-vX.Y.Z.tar.gz` and `grandma-linux-vX.Y.Z.tar.gz.sha256`. The updater requires the archive's SHA256 digest from the GitHub API. Build from a clean tagged checkout with:

```sh
python3 scripts/build-release.py v0.1.0 --output /tmp/grandma-release
```

Release automation does not establish hardware support. Keep the known limits in the release notes and complete the applicable checks in [Testing](../TESTING.md).
