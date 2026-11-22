# Prepare a release

All changes to main require a reviewed pull request. Complete the applicable checks in [Testing](../TESTING.md) and record known limits in the release notes.

1. Merge the tested changes through the pull request.
2. In GitHub Actions, run **Prepare release draft** on main with a new version such as `v0.1.0`.
3. Review the draft notes, source revision and attached archive/checksum.
4. Publish the draft after release acceptance. Do not label untested hardware as supported.
5. Test installation and update from that published version on the disposable VM before using it on the target PC.

The workflow does not push source changes or publish the draft automatically. It runs local checks, builds `grandma-linux-vX.Y.Z.tar.gz` and its checksum, and creates a release draft targeting the selected main commit. It refuses an existing tag. The archive VERSION is the release version; SOURCE_REVISION identifies the source commit. The source tree can remain marked as development until the next release.

For a local package from a clean checkout:

```sh
python3 scripts/build-release.py v0.1.0 --output /tmp/grandma-release
```

Upload the generated archive as a release asset, not GitHub's automatic source archive. The updater requires the asset's SHA256 digest from the GitHub API. Do not reuse a version for changed content. Publish a new patch release instead.
