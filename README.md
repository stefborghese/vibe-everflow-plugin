# Vibe -> Everflow Sync Plugin

A Claude / Cowork plugin that runs the daily Vibe -> Everflow conversion sync.

## What it does

1. Reads 4 CSV exports you drop into a folder
2. Dedupes conversions against an existing Everflow export
3. Flags cross-attribution between paid media and affiliates
4. Distributes total daily spend across kept conversions as payout
5. Writes an Everflow Conversion Import CSV
6. Posts a clean summary to Slack `#aor-reporting`

You upload the generated CSV to Everflow manually.

## Installation

In Cowork or Claude Code, add the marketplace once:

```
/plugin marketplace add <GITHUB_USERNAME>/vibe-everflow-plugin
```

Then install the plugin:

```
/plugin install vibe-everflow-sync@vibe-everflow-marketplace
```

See [COLLEAGUE_SETUP.md](./COLLEAGUE_SETUP.md) for a full walkthrough.

## Daily use

1. Drop the 4 CSVs into your chosen folder:
   - `cpg_weekly_dashboard.csv` (Vibe conversions)
   - `campaigns_export_*.csv` (Vibe spend — one or more)
   - `ConversionsExport_*.csv` (Everflow export)
   - `brand_mapping.csv` (your brands; copy from `skills/vibe-everflow-sync/templates/`)
2. Tell Cowork: **"run the vibe everflow sync"**
3. Review the Slack summary, then upload the CSV to Everflow.

## Brand mapping

Edit `brand_mapping.csv` to add or remove brands. No code changes needed.

```
brand_name,offer_id,revenue
Bath Mate,1314,60
Paw Origins,1386,40
```

## Target dates

- **Monday** run: Wed, Thu, Fri, Sat, Sun
- **Other days**: yesterday + 2 safety-net days (T-1, T-2, T-3)

## Files

- `.claude-plugin/plugin.json` — plugin manifest
- `.claude-plugin/marketplace.json` — marketplace listing
- `skills/vibe-everflow-sync/SKILL.md` — Cowork instructions
- `skills/vibe-everflow-sync/scripts/vibe_to_everflow.py` — the sync script
- `skills/vibe-everflow-sync/templates/brand_mapping.csv` — starter mapping
