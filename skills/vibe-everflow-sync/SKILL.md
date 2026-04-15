---
name: vibe-everflow-sync
description: Run the daily Vibe -> Everflow conversion sync. Triggers on "vibe sync", "run the vibe everflow sync", "daily conversion upload", "vibe conversions to everflow", or similar. Reads 4 CSVs from an upload folder, dedupes against Everflow, distributes spend as payout, writes an Everflow conversion-import CSV, and prints a Slack-ready summary.
---

# Vibe -> Everflow Conversion Sync

You are running the daily Vibe -> Everflow conversion sync for a CPG affiliate program.

## Inputs

The user drops 4 CSV files into their upload folder BEFORE running this skill:

1. `cpg_weekly_dashboard.csv` — Vibe conversions export (full week works; script filters to target dates)
2. `campaigns_export_*.csv` — Vibe daily spend export (one or more files; script globs them)
3. `ConversionsExport_*.csv` — Everflow conversions export used for dedup
4. `brand_mapping.csv` — columns: `brand_name,offer_id,revenue` (user maintains this; a template ships with the plugin)

## Target date window (Argentina time)

- **Monday**: Fri + Sat + Sun (new uploads) + Wed + Thu (safety net) = 5 days
- **Tue-Sun**: yesterday + 2 days before (safety net) = 3 days

The script picks the dates automatically.

## Steps

1. **Confirm the upload folder.** If the user has not told you, ask them where the 4 CSVs are located. Default: the folder they have currently selected in Cowork. If they say "my downloads" or similar, have them move the files to the selected folder first. The 4 files must all live in the same folder.

2. **Confirm the output folder.** Default: same as the upload folder, or the selected folder.

3. **Run the script.** Use Bash:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/vibe-everflow-sync/scripts/vibe_to_everflow.py" \
     --upload-dir "<UPLOAD_DIR>" \
     --output-dir "<OUTPUT_DIR>" \
     --affiliate-id 445
   ```

   Replace `<UPLOAD_DIR>` and `<OUTPUT_DIR>` with actual paths. `--affiliate-id` defaults to 445; override only if the user says so.

4. **Present the output CSV** to the user using `computer://` link format. The script prints the CSV path at the end under `[CSV Path]`.

5. **Post the Slack summary.** The script prints a `[Slack Message Preview]` block. Post that message VERBATIM to Slack channel `#aor-reporting` (ID `C099G2PPR4Y`) using the Slack MCP's `slack_send_message` tool. Do NOT edit the copy, do NOT add emojis, do NOT add preamble.

6. **Next step for the user:** tell them to upload the CSV to Everflow via the Conversion Import UI. This plugin does not call the Everflow API.

## Dedup rules (handled by the script, for your awareness)

Per `order_id` vs. Everflow export:
- Match under affiliate 445 -> **skip silently** (already uploaded)
- Match approved/pending under a different affiliate -> **skip + flag cross-attribution** in Slack summary
- Match only rejected under other affiliates -> **upload with `#` prefix** on the order_id
- No match -> **upload normally**

## Payout

Total brand spend across the window is split evenly across the kept (post-dedup) rows for that brand. Cent remainder lands on the first row.

## adv5

Vibe's `Is First Order ?` is FLIPPED for Everflow's `adv5`: Vibe `true` -> EF `false`, Vibe `false` -> EF `true`.

## Errors

- Missing `brand_mapping.csv` or `cpg_weekly_dashboard.csv` -> script exits with a `[FATAL]` message. Relay that to the user and ask them to drop the file.
- Missing `campaigns_export_*.csv` -> script warns; payouts will all be $0. Ask the user if they want to proceed without spend.
- Missing `ConversionsExport_*.csv` -> script warns; dedup is skipped. Confirm with the user before uploading.

## Do not

- Do not modify the script's output file or Slack message.
- Do not upload to Everflow programmatically; the user does that manually.
- Do not guess missing brand offer IDs or revenue values — if a brand appears in the dashboard but not in `brand_mapping.csv`, the script skips it. Tell the user which brand is missing so they can add it to the mapping CSV and rerun.
