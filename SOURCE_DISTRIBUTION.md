# GPL source distribution guide — LinguaNova

Release-notice baseline date: 2026-10-16

This guide does not replace the GNU GPL text in `LICENSE` / `COPYING`.

## Source-only publication

A public source repository should include, at minimum:

- the complete LinguaNova source for the published revision;
- `LICENSE` and `COPYING`;
- `NOTICE.md`;
- `UPSTREAM.md`;
- `LICENSE_POLICY.md`;
- `MODIFICATIONS_LINGUANOVA.md`;
- build scripts and build-control files;
- dependency metadata;
- third-party notices applicable to files actually included in the repository.

## Binary distribution

For every binary release of LinguaNova:

1. identify the exact source commit/tag used to build it;
2. make the Complete Corresponding Source for that binary available in a GPL-compliant manner;
3. retain build scripts/configuration used to control compilation and packaging;
4. keep upstream and modification notices;
5. include applicable third-party notices/licenses for components actually bundled;
6. do not provide source from a different release and describe it as matching source.

## Recommended GitHub release layout

For a release such as `v1.0.0`, publish clearly named artifacts, for example:

- `LinguaNova_Setup_1.0.0.exe`
- `LinguaNova_Portable_1.0.0.zip`
- `LinguaNova-1.0.0-source.zip`
- `SHA256SUMS.txt`

The source archive should come from the same tagged revision used for the binaries.

## GitHub-generated source archives

GitHub automatically offers source archives for tags. They can be useful, but before relying on them as the sole Corresponding Source, verify that the repository/tag contains all source and build-control material required to rebuild the distributed program, subject to GPL exceptions.

For clarity, LinguaNova's release process should also produce an explicitly named matching source archive.

## Installers and portable builds

An installer or portable archive does not change the GPL source obligation.

The updater must not make source access harder than binary access in a way that defeats the applicable GPL distribution method chosen for the release.

## Public updater

The public LinguaNova updater is intentionally disabled until the official LinguaNova repository exists and is configured.

It must not use RenLocalizer as a fallback update source.

## Private use

GPL does not require publication merely because a private modified copy exists. Distribution/conveying is what triggers the relevant source obligations described by the license.

## Release checklist

See `docs/RELEASE_CHECKLIST.md`.

This guide is practical compliance documentation, not individualized legal advice.
