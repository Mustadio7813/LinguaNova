# Third-party notices and release-audit policy — LinguaNova

LinguaNova depends on third-party software and may interact with external services.

This file is intentionally transparent about the difference between:

1. dependencies declared by the source project;
2. components downloaded separately at runtime;
3. external network services;
4. the exact set of files that will eventually be bundled in a compiled release.

## Known project/runtime components

The current source declares or documents components including:

- PyQt6 / Qt — desktop GUI and QML runtime;
- aiohttp — asynchronous HTTP;
- requests — HTTP;
- charset-normalizer — text/encoding handling;
- orjson — JSON handling;
- py3langid — language identification;
- openai — client library for compatible API use;
- google-genai — Google Gemini client;
- unrpa — RPA archive extraction;
- rpycdec — complementary RPYC handling;
- rich — CLI output;
- PyYAML — YAML handling;
- fonttools — font inspection/manipulation.

The build process also uses development/build dependencies such as PyInstaller.

## Components downloaded separately

Some optional runtimes or models may be downloaded by the user or by LinguaNova on request. A separately downloaded component is not automatically part of the LinguaNova source license merely because LinguaNova can launch or manage it.

Its own license and notices still apply.

## External services

Translation providers and APIs are not relicensed by LinguaNova. Their services, SDKs and endpoints are subject to their own licenses and/or terms of service.

## IMPORTANT: final binary audit is still required

The final Windows/Linux/macOS executable has not yet been frozen for this GitHub-preparation snapshot.

Therefore this file does **not** pretend to be the final exhaustive binary notice bundle.

Before publishing each compiled release:

1. resolve the exact dependency versions used by the release environment;
2. inspect the PyInstaller/packaging output to identify what is actually bundled;
3. collect the license/copyright notices required by those bundled components;
4. include those notices with the binary distribution where required;
5. repeat the audit whenever dependency versions or packaged files change.

This is especially important for Qt/PyQt6 and any libraries copied into the distributed application.

## No removal of third-party notices

Do not strip third-party copyright or license notices from bundled components.

## Release record

The exact release inventory should be recorded alongside the release tag/build record rather than inferred later from a moving development environment.
