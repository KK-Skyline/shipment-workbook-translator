[![Tests](https://github.com/KK-Skyline/shipment-workbook-translator/actions/workflows/tests.yml/badge.svg)](https://github.com/KK-Skyline/shipment-workbook-translator/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange)
![Runtime: Local](https://img.shields.io/badge/Runtime-Local-198754)

# Shipment Workbook Translator

**Turn shipment spreadsheet facts into typed, traceable planning inputs.**

面向物流工作簿的确定性转译核心：把单元格快照转换成带来源证据的物流中间表示，
在输入缺失、冲突或不受支持时返回结构化错误。

```text
Your XLSX adapter → RawCell[] → profile / row / group validation
                             → TranslationResultV1
                               ├─ typed IR + cell provenance + canonical bytes + SHA-256
                               └─ typed error + phase + source-cell evidence
```

The core runs locally with the Python standard library. It makes no model calls,
requires no API key, and performs no workbook or network I/O.

## Why it exists

This code grew out of a logistics planning application that explored using large
language models to propose loading plans. That application did not reach its intended
delivery goal. We are publishing the deterministic input boundary as a focused,
inspectable component, together with an honest account of its limits.

Its useful job is to make source facts explicit before another system uses them.
It does **not** establish that a loading plan is physically safe or commercially ready.

## What is included

- Three implemented profiles: `canonical_split.v1`, `combined_dimension.v1`, and
  `global_packing_explicit_semantics.v1`.
- Row, physical carton-group, aggregate load-unit and conservation records.
- Per-field source-cell coordinates and derivation rules.
- Typed failures through intake, grammar, merge, profile, row, group, conservation
  and canonical-output phases (P0–P7).
- Decimal arithmetic, explicit merge/formula-cache states, resource checks,
  deterministic canonical JSON bytes and an output digest.
- A synthetic example and a small standalone public-API regression suite.

The extraction preserves the core implementation apart from its `RawCell` import.
It does not include the original desktop UI, cloud integration, solver, customer
workbooks, temporary evidence archives, or historical contract bundles.

## Quick start

```bash
git clone https://github.com/KK-Skyline/shipment-workbook-translator.git
cd shipment-workbook-translator
python -m pip install .
python -m examples.basic
python -B -m unittest discover -s tests -v
```

Python 3.11 or newer is required. CI is configured for 3.11–3.14; the workflow badge
reports the actual CI outcome rather than a manually asserted pass.

```python
from shipment_translator import translate_shipment_workbook
from examples.basic import sample_cells  # synthetic demonstration only

result = translate_shipment_workbook(sample_cells())
if result.ok:
    print(result.ir.rows[0].qty_pcs)
    print(result.ir_sha256)
else:
    print(result.error.phase, result.error.code, result.error.source_cells)
```

For real XLSX files, supply an adapter that creates `RawCell` records. Preserve
coordinates, raw types, display text, merge declarations and formula-cache status.
Do not flatten merged cells into guessed values or evaluate missing formula caches.
This release intentionally starts at the in-memory boundary; it has no XLSX reader CLI.

See [the input and output guide](docs/INTERFACE.md) for the verified public shape.

## Explicit packing facts

Packing must be declared by a supported field. In the global profile, use
`packing_type` or `装载类型` with `pallet` / `loose` or `整托` / `散件`.
Pallet counts, envelopes, weights and text in `Pallet Size` cannot substitute for
that declaration. A true vertical merge may declare a group from its top-left;
ordinary blank continuation cells do not imply inheritance.

Profile aliases differ: the canonical example uses `packing_type`; consult the
profile metadata in the source before preparing another template.

## Where it fits — and where it stops

Good fit: controlled packing-list templates, auditable import pipelines, local
validation before cloud calls, and reproducible input facts for downstream solvers.

Limits:

- It supports specific header/profile semantics, not arbitrary visual spreadsheets.
- It does not infer missing business facts from images, colors, filenames or layout.
- It is one-way: source cells become IR; original workbook layout is not reconstructed.
- It does not optimize container loading or validate pallet ratings and handling safety.
- Successful translation can still carry `required_t2_block`; callers must honor it.
- Current code is a large, specialized module with substantial historical complexity.
  This alpha extraction is not a claim of complete conformance or formal verification.
- Resource guards are not a process sandbox. Apply independent input, memory and time
  limits before exposing it to untrusted workloads; XLSX archive validation belongs
  to the adapter.

The original application's historical test counts do not describe this standalone
release. Its current verification is the checked-in suite and published CI.

### Known security issue — fix pending

The current merge-overlap sweep can amplify memory consumption for malicious,
overlapping merge declarations despite passing its area/count guards (CWE-400).
Do not deploy this alpha release as an in-process parser for untrusted workloads.
The maintainer elected to publish this snapshot with the issue documented and
delegate remediation to Claude with independent review. See the
[repair handoff](docs/CLAUDE_HANDOFF.md) for evidence and acceptance criteria.
The Codex Security audit did not complete because its local report storage failed
a permissions check; no completed security-audit attestation is claimed.

## Contributing

Provide synthetic inputs and independently stated expected facts, source references
and errors. Include a public-entry regression for correctness changes. Avoid tests
that derive expected provenance from production lookup tables or from the actual
result. Keep parser behavior changes explicit; a larger passing-test count alone
does not demonstrate correct semantics.

Please do not attach customer spreadsheets, credentials or private shipment data.
See [SECURITY.md](SECURITY.md) and [AUTHORS.md](AUTHORS.md).

## Authors

Created and maintained by **KK-Skyline**, with engineering, review, testing and
documentation assistance from **Codex (OpenAI)**. Codex is an AI programming
assistant; this credit does not imply OpenAI endorsement.

## License

[MIT](LICENSE) · Copyright © 2026 KK-Skyline.
