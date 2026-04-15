# GitHub Setup (for Stef)

One-time setup so your colleague can install the plugin. GitHub is free for public repos — no credit card needed.

## 1. Create a GitHub account

1. Go to https://github.com/signup
2. Use your email, pick a username (e.g. `stef-aor`), create a password
3. Verify your email

## 2. Create a new repository

1. Click the **+** in the top-right -> **New repository**
2. Repository name: `vibe-everflow-plugin`
3. Set it to **Public** (required so Claude Code can fetch it without auth)
4. **Do NOT** check "Add a README" — we already have one
5. Click **Create repository**

GitHub will show a page with quick setup commands. Leave that tab open.

## 3. Upload the plugin files

Easiest path: drag-and-drop in the browser.

1. On the new repo page, click **uploading an existing file** (small link under "Quick setup")
2. Open the `vibe-everflow-plugin` folder on your computer
3. Select **everything inside** the folder (not the folder itself) — you should see:
   - `.claude-plugin/`
   - `skills/`
   - `README.md`
   - `GITHUB_SETUP.md`
   - `COLLEAGUE_SETUP.md`
4. Drag all of it into the browser upload area
5. Scroll down, in the commit message box type: `initial plugin`
6. Click **Commit changes**

> If the `.claude-plugin` folder doesn't upload (browsers sometimes hide dotfolders), do this instead: click **Add file -> Create new file**, then in the filename box type `.claude-plugin/plugin.json` — GitHub will create the folder for you. Paste the contents of your local `plugin.json` and commit. Repeat for `.claude-plugin/marketplace.json`.

## 4. Verify

Visit `https://github.com/<YOUR_USERNAME>/vibe-everflow-plugin` — you should see all files listed, with the README rendered below.

## 5. Share with your colleague

Send her `COLLEAGUE_SETUP.md` plus your GitHub username. She'll need to run:

```
/plugin marketplace add <YOUR_USERNAME>/vibe-everflow-plugin
/plugin install vibe-everflow-sync@vibe-everflow-marketplace
```

## Pushing updates later

When you need to ship an update:

1. On GitHub, navigate to the file you want to change
2. Click the pencil icon (Edit)
3. Make changes, scroll down, commit
4. Bump the `version` in `.claude-plugin/plugin.json` so your colleague's Cowork knows to refresh

Your colleague will pick up the new version the next time she runs `/plugin update` or reinstalls.

## Want a fancier workflow?

If you get comfortable, install [GitHub Desktop](https://desktop.github.com/) — it gives you a click-to-commit GUI on your machine so you can edit files locally and sync with one button. Not required.
