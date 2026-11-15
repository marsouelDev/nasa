# AGENTS.md

## Repo at a glance

Tiny workspace (3 files, **not a git repo**) for the French-language "AgroSentry Cameroun" hackathon:
turn NASA Earth-observation data into sowing/rotation advice for smallholders (pilot zone **Bafia**,
~4.75°N, 11.23°E).

- `Cahier_des_charges_AgroSentry_Cameroun_v4_2.docx` — single source of truth (spec, in French).
  Read it before changing scope, data sources or rotation logic.
- `nasa_power_edea.py` — standalone NASA POWER fetch + CSV + rainfall/temperature plot.
- `download-all-2026-11-14_15-29-10.py` — untouched ASF-generated bulk downloader for two NISAR L0B
  HDF5 files. Per spec §18 this raw radar product is out of MVP scope: don't debug or extend it,
  and don't edit the generated file unless explicitly asked.

The stack described in the spec (FastAPI, Pandas/Scikit-Learn/Prophet, React+Vite PWA, Leaflet,
SQLite, Africa's Talking SMS) and the prototypes it mentions (`agrosentry_carte_gibs.html`,
`agrosentry_model.py`) **do not exist in this directory yet**. Treat them as a plan, not as code
you can import or wire up.

## Running

- `python nasa_power_edea.py` from the repo root. System Python is 3.14.3; `requests` and `pandas`
  are installed, **`matplotlib` is not** — the script dies on import until you `pip install matplotlib`.
- Outputs `nasa_power_edea.csv` (UTF-8 with BOM, for Excel FR) and `nasa_power_edea.png` in the
  current directory. It ends on `plt.show()`, which blocks a non-interactive run; use
  `MPLBACKEND=Agg` and/or skip `show()` for batch runs. No CSV/PNG is checked in.
- No tests, lint, typecheck or CI. Verification = run the script and sanity-check the CSV
  (row count, column names, no `-999` left).
- The ASF downloader prompts interactively for Earthdata credentials, caches cookies in
  `~/.bulk_download_cookiejar.txt`, writes multi-GB files into the CWD and skips files whose size
  already matches the remote. Don't launch it casually.

## Gotchas

- `nasa_power_edea.py` hardcodes **Edéa** (3.80, 10.13) and 2025 (`AAAAMMJJ` strings), while the
  spec's pilot zone is **Bafia**. Confirm coordinates/period before extending the pipeline; don't
  silently overwrite them.
- NASA POWER daily point API: `community=AG`, dates `YYYYMMDD`; missing values come back as `-999`
  and must be replaced before any stats (the script does this).
- Every run hits the network; there is no local cache, although the spec requires one ("cache local").
- Keep comments, docstrings, printed messages and any user-facing text **in French**, matching the
  existing code and deliverables; preserve `encoding="utf-8-sig"` on CSV export.
