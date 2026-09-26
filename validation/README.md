# Local candidate qualification — 25 September 2026

**102 passed, zero skips**, with the predecessor's retained Google Imagen SDK
deprecation warning: 94 unchanged module tests plus 8 new bundle checks.
See [machine receipt](offline-qualification.json) and [test output](offline-tests.txt).

The isolated Python 3.13.11 environment resolved published **Core 2.0.1**,
Foundation main `89575c3482e3e8afe5a03df72e723cf815fa1f6c`, skills main
`402ee0d1e75f2d13e8b090d2b10c716cd60f526d`, OpenAI 3.19.2 and Google GenAI 2.25.0.
Resolution used public PyPI, matching the supported host graph. An initial inherited
corporate feed resolved Core 1.6.1, on which the original 94 module tests also
passed; that was not used as the final supported-runtime qualification.

Verified behavior:

- Thin root, full behavior and skills-only behavior resolve from an unrelated
  working directory through actual Foundation composition.
- Skill discovery uses `@imagegen:skills` and loads the unchanged `imagegen` body.
  Existing sources and visibility policy remain intact when composed first.
- Source activation uses a `file://` root with `#subdirectory=modules/tool-image`,
  the real Foundation resolver/activator, and Core validation/loading. Source
  resolution is not mocked. Dependencies were installed beforehand in isolation.
- A missing backend permits mounting and safe capability inspection but refuses
  generation. A final host `allow_paid: false` override also refuses generation
  with an otherwise configured synthetic backend; neither creates output claims.
- All nine module implementation/type-marker files, every predecessor test file,
  and the skill body match their attributed sources byte-for-byte.
- Wheel/sdist build succeeds. Wheel implementation bytes match source, original
  entry points remain intact, notices are packaged, and no bytecode is present.

All tests prohibit network calls. Initial test-harness mistakes in calling the
Core-bound mount closure and comparing a source wrapper were corrected without
changing runtime implementation or weakening checks; original failure logs remain
in the ignored local validation directory.

These are local candidate results, not remote Git installation, installed-host,
paid generate/edit, Google account, browser/pixel presentation or Windows
acceptance. Prior real acceptance remains attributed to the predecessor, as
explained in [provenance](../PROVENANCE.md). Exact resolved revisions here are run
evidence; manifests continue to track `@main`.

The two unchanged predecessor files `tool.py` and `tests/test_tool.py` retain
their original trailing whitespace. New and adapted files pass whitespace checks;
the relocation deliberately avoids normalizing implementation or test bytes.
