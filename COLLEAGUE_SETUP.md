# Colleague Setup

One-time install, then daily use takes ~2 minutes.

## Prerequisite

You're using Cowork (the Claude desktop app) or Claude Code. Python 3.9+ must be on your machine (Cowork already has it in the sandbox).

## One-time install

Open Cowork. In the chat, run:

```
/plugin marketplace add <STEF_GITHUB_USERNAME>/vibe-everflow-plugin
```

Then:

```
/plugin install vibe-everflow-sync@vibe-everflow-marketplace
```

You should see confirmation the plugin is installed.

## Slack connector

The plugin posts a summary to `#aor-reporting`. Make sure the Slack MCP connector is enabled in your Cowork settings and that you're authorized to post in that channel.

## Pick a working folder

Pick a folder on your computer to use as the Vibe -> Everflow workspace. For example: `~/Documents/vibe-sync/`. Select it in Cowork as your working folder.

Copy the starter `brand_mapping.csv` from the plugin into that folder. You can ask Cowork to do it:

> "Copy the brand_mapping.csv template from the vibe-everflow-sync plugin into my selected folder."

## Daily routine

Every morning (weekdays):

1. In **Vibe**, export the CPG weekly dashboard CSV -> save as `cpg_weekly_dashboard.csv` in your working folder
2. In **Vibe**, export the campaigns spend CSV for the target window -> save as `campaigns_export_<anything>.csv` in your working folder
3. In **Everflow**, export the conversions CSV for the last few days -> save as `ConversionsExport_<anything>.csv` in your working folder
4. In Cowork, say: **"run the vibe everflow sync"**

Cowork will:
- Run the script
- Show you the generated Everflow import CSV
- Post a summary to `#aor-reporting` on Slack

Then upload the generated CSV to Everflow via the Conversion Import UI.

## Updating brand_mapping.csv

If a new brand goes live, open `brand_mapping.csv` in your working folder and add a row:

```
New Brand Name,<offer_id>,<revenue>
```

Save. Next run picks it up. No plugin update needed.

## Getting help

If something breaks, send Stef the error message from Cowork and the contents of your `brand_mapping.csv`.
