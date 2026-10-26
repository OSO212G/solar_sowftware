# Verification scope

## Exercised environment and setup

Windows 11, CPython 3.12.13; pvlib 0.15.1, pandas 3.0.2, numpy 2.4.4, scipy 1.17.1, Streamlit 1.56.0, fpdf2 2.8.7, pytest 9.0.3 and setuptools 82.0.1. The full dependency resolution is in `uv.lock`.

An empty local virtual environment was installed by `uv sync --frozen --offline --python <Python-3.12>` using an existing dependency cache; exit 0. A subsequent actual `uv sync --locked --offline --python <Python-3.12>` exited 0. No dependency downloads were needed. This proves this cache-backed local setup, not an uncached machine, online acquisition or all supported Python versions.

The inherited lock marked the project root `virtual` despite the declared build backend. The original locked/offline dry-run failed while attempting resolution (uncached folium for a Python >=3.14 split). The single metadata correction changes only that root source to `editable`; every dependency name/version is unchanged. The corrected locked/offline dry-run succeeded without resolving new versions. Do not infer a universal dependency problem or a verified online installer from that initial failure.

## What ran in this presentation edition

- Affected tests in both the original reusable stack and the newly installed local environment: **4 passed, 6 provider-dependent skipped, 73 deselected**, exit 0. Selection covers retained report helpers, initial settings render and synthetic real-engine integration. Two other provider-dependent tests belong to the deselected set, not newly accepted coverage.
- The changed results page was exercised with Streamlit `AppTest` and synthetic state, without a server/browser or providers. It rendered with no exceptions; its unsupported interval was absent and the loss-boundary labels were present.
- A real wheel was built with the installed pinned backend, including component CSV/JSON. Byte-compilation-disabled warnings are retained as build warnings, not failures.
- The exact final source ZIP was extracted and its offline demo executed in a fresh output directory using the newly installed dependency environment. The demo imports the extracted source, not an installed-wheel entrypoint. Whole result JSON values match the preserved baseline demo exactly; PDF bytes/layout are not expected to match.
- Actual self-contained SVGs and their README placement were rendered by existing headless Edge at normal and narrow viewports. Private screenshots are not shipped as public assets. Local preview is not GitHub remote-render acceptance.

The original unchanged baseline's **75 passed / 8 external-provider skips** is inherited evidence, not a new full-suite result for this edition. No full provider suite was rerun.

## Three different kinds of check

**Behavioral checks:** schema-reference rejection, selected SQLite lifecycle and electrical/formula expectations test their defined implementation contracts; they do not establish physical/regulatory correctness.

**Artifact smoke checks:** the demo verifies a PDF header/minimum size, a SQLite round-trip and nonzero polygon packing. File existence is not a BOM-quantity, PDF parsing or visual-quality check. The generated PDF is not publicly distributed or visually qualified.

**Known-defect characterization:** the synthetic integration records monthly-before-loss energy exceeding annual-after-loss energy. The retained corner-containment probe records panel corners outside a boundary. These passing assertions describe defects; neither is a numerical/geometry accuracy result. The affected selection does not rerun the corner probe.

## Offline boundary and output

The demo/test wrappers deny Python socket connect/address lookup, subprocess launch and shell-system events after startup. This is cooperative scaffolding, not an OS sandbox. Weather retrieval alone is patched; actual model functions execute. Matplotlib uses Agg. Provider-dependent tests remain explicitly skipped.

The clear-sky fixture has 8,760 hourly records for 2025 and an explicit Asia/Kuala_Lumpur timezone. Observed annual after-loss energy is **12789.316312684909 kWh**; before-loss monthly sum is **14217.995266420818 kWh**; separate layout exercise yields **121 panel centers**. These are reproducible implementation observations, not a site prediction, uncertainty bound or measured accuracy.

No live provider, map workflow, hosting, hardware, safety, policy currency or production acceptance is claimed. No original DB/cache, generated report, private execution path, history or raw preparation evidence belongs in the public file set.
