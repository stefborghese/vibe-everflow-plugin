#!/usr/bin/env python3
"""
Vibe -> Everflow conversion sync (file-based, no API calls).

Reads from an upload folder (default: ./vibe upload):
  - cpg_weekly_dashboard.csv         Vibe conversions export
  - campaigns_export_*.csv           Vibe daily spend export (1+ files)
  - ConversionsExport_*.csv          Everflow conversions export for dedup
  - brand_mapping.csv                brand_name, offer_id, revenue

Target dates (America/Argentina/Buenos_Aires):
  - Monday   -> Fri, Sat, Sun (upload) + Wed, Thu (safety net) = 5 days
  - Other    -> yesterday + 2 days before (safety net) = 3 days

Dedup rule (per order_id):
  - Any EF match under the configured affiliate -> skip silently
  - Else any EF match approved/pending          -> skip + flag cross-attribution
  - Else all EF matches rejected                -> upload with '#' prepended
  - No EF match                                 -> upload normally

Payout: total brand spend across the window distributed evenly across
kept (post-dedup) rows for that brand (cent remainder on first row).

adv5 flip: Vibe "Is First Order ?" true <-> false vs Everflow.

Usage:
    python3 vibe_to_everflow.py \\
        --upload-dir "./vibe upload" \\
        --output-dir "./vibe automation" \\
        --affiliate-id 445
"""

import argparse
import csv
import glob
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")
ART_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

DASHBOARD_FILE = "cpg_weekly_dashboard.csv"
SPEND_GLOB = "campaigns_export_*.csv"
EF_EXPORT_GLOB = "ConversionsExport_*.csv"
MAPPING_FILE = "brand_mapping.csv"


# --- Helpers --------------------------------------------------------------

def get_target_dates(today=None):
    if today is None:
        today = datetime.now(ART_TZ).date()
    weekday = today.weekday()
    if weekday == 0:  # Monday
        return [today - timedelta(days=d) for d in (5, 4, 3, 2, 1)]
    return [today - timedelta(days=d) for d in (3, 2, 1)]


def parse_money(s):
    if s is None:
        return 0.0
    s = str(s).strip()
    if not s or s == "-":
        return 0.0
    return float(s.replace("$", "").replace(",", "").strip() or 0)


def parse_date_ymd(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_date_mdy(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%m/%d/%Y").date()
    except ValueError:
        return None


def date_to_epoch_midnight_et(d):
    dt = datetime(d.year, d.month, d.day, tzinfo=NY_TZ)
    return int(dt.timestamp())


def flip_first_order(v):
    s = (v or "").strip().lower()
    if s == "true":
        return "false"
    if s == "false":
        return "true"
    return ""


# --- Loaders --------------------------------------------------------------

def load_brand_mapping(path):
    mapping = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = (row.get("brand_name") or "").strip()
            if not name:
                continue
            try:
                mapping[name] = {
                    "offer_id": int(str(row.get("offer_id", "")).strip()),
                    "revenue": float(str(row.get("revenue", "")).strip()),
                }
            except ValueError:
                print(f"[Mapping] WARNING: bad row, skipping: {row}")
    print(f"[Mapping] Loaded {len(mapping)} brands: {sorted(mapping)}")
    return mapping


def load_dashboard(path, target_dates, brand_mapping):
    target_set = set(target_dates)
    rows = []
    skipped_brand = Counter()
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return [], {}
        idx = {h.strip(): i for i, h in enumerate(header)}
        name_i = idx.get("Advertiser Name")
        att_i = idx.get("Attributed Event America/NY Date")
        pid_i = idx.get("Purchase ID")
        first_i = idx.get("Is First Order ?")
        price_i = idx.get("Purchase ($)")

        if any(v is None for v in (name_i, att_i, pid_i, price_i)):
            raise SystemExit(f"[Dashboard] Missing required columns. Header: {header}")

        for row in reader:
            if not row or all(not (c or "").strip() for c in row):
                continue
            brand = (row[name_i] or "").strip()
            att_date = parse_date_ymd(row[att_i])
            if att_date is None or att_date not in target_set:
                continue
            if brand not in brand_mapping:
                skipped_brand[brand] += 1
                continue
            rows.append({
                "brand": brand,
                "event_date": att_date,
                "order_id": (row[pid_i] or "").strip(),
                "is_first": (row[first_i] or "").strip() if first_i is not None else "",
                "sale_amount": parse_money(row[price_i]),
            })
    print(f"[Dashboard] {len(rows)} rows for target dates {sorted(target_set)}")
    if skipped_brand:
        print(f"[Dashboard] Skipped (brand not in mapping): {dict(skipped_brand)}")
    return rows, dict(skipped_brand)


def load_spend(paths, target_dates):
    target_set = set(target_dates)
    spend = defaultdict(float)
    rows_seen = 0
    for path in paths:
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                rows_seen += 1
                period = (row.get("Period") or "").strip()
                brand = (row.get("Advertiser name") or "").strip()
                spend_raw = row.get("Spend") or ""
                if not period or not brand or brand.lower().startswith("total"):
                    continue
                d = parse_date_mdy(period.split(" - ")[0].strip())
                if d is None or d not in target_set:
                    continue
                spend[(brand, d)] += parse_money(spend_raw)
    print(f"[Spend] {rows_seen} campaign rows from {len(paths)} file(s); "
          f"{len(spend)} (brand,date) combos for target dates")
    return spend


def load_ef_export(paths):
    if not paths:
        return {}
    path = max(paths, key=lambda p: os.path.getmtime(p))
    print(f"[EF] Loading dedup data from {os.path.basename(path)}")
    ef_map = defaultdict(list)
    total = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            total += 1
            oid = (row.get("order_id") or "").strip()
            if not oid:
                continue
            try:
                aff_id = int(str(row.get("network_affiliate_id") or "0").strip() or 0)
            except ValueError:
                aff_id = 0
            ef_map[oid].append({
                "status": (row.get("conversion_status") or "").strip().lower(),
                "affiliate_id": aff_id,
                "affiliate_name": (row.get("network_affiliate_name") or "").strip(),
                "offer_name": (row.get("network_offer_name") or "").strip(),
                "date": (row.get("date") or "").strip(),
            })
    print(f"[EF] Indexed {len(ef_map)} unique order_ids from {total} conversions")
    return ef_map


# --- Dedup ----------------------------------------------------------------

def classify_dedup(ef_matches, affiliate_id):
    if not ef_matches:
        return "upload", None
    ours = [m for m in ef_matches if m["affiliate_id"] == affiliate_id]
    if ours:
        return "skip_ours", {"status": ours[0]["status"]}
    active = [m for m in ef_matches if m["status"] in ("approved", "pending")]
    if active:
        partners = Counter((m["affiliate_name"] or f"aff_{m['affiliate_id']}", m["status"]) for m in active)
        return "skip_crossatt", {"partners": dict(partners)}
    rejected = [m for m in ef_matches if m["status"] == "rejected"]
    if rejected:
        partners = Counter(m["affiliate_name"] or f"aff_{m['affiliate_id']}" for m in rejected)
        return "upload_hash", {"partners": dict(partners)}
    return "upload", None


# --- Transform ------------------------------------------------------------

def build_output(dashboard_rows, ef_map, brand_mapping, spend_map, affiliate_id):
    kept = []
    skipped_ours = 0
    cross_att = []
    hashed = []

    for r in dashboard_rows:
        action, info = classify_dedup(ef_map.get(r["order_id"], []), affiliate_id)
        if action == "skip_ours":
            skipped_ours += 1
            continue
        if action == "skip_crossatt":
            cross_att.append({"brand": r["brand"], "order_id": r["order_id"], "partners": info["partners"]})
            continue
        if action == "upload_hash":
            r = {**r, "order_id": f"#{r['order_id']}"}
            hashed.append({"brand": r["brand"], "order_id": r["order_id"], "partners": info["partners"]})
        kept.append(r)

    brand_spend = defaultdict(float)
    for (brand, _d), amt in spend_map.items():
        brand_spend[brand] += amt

    kept_by_brand = defaultdict(list)
    for r in kept:
        kept_by_brand[r["brand"]].append(r)

    payout_by_row_id = {}
    for brand, items in kept_by_brand.items():
        total = brand_spend.get(brand, 0.0)
        n = len(items)
        if n == 0:
            continue
        if total <= 0:
            payouts = [0.0] * n
        else:
            base = round(total / n, 2)
            total_base = round(base * n, 2)
            remainder = round(total - total_base, 2)
            payouts = [base] * n
            payouts[0] = round(payouts[0] + remainder, 2)
        for r, p in zip(items, payouts):
            payout_by_row_id[id(r)] = p

    csv_rows = []
    for r in kept:
        cfg = brand_mapping[r["brand"]]
        csv_rows.append({
            "offer_id": cfg["offer_id"],
            "affiliate_id": affiliate_id,
            "event_id": 0,
            "payout": f"{payout_by_row_id.get(id(r), 0.0):.2f}",
            "revenue": cfg["revenue"],
            "sale_amount": f"{r['sale_amount']:.2f}",
            "unix_timestamp": date_to_epoch_midnight_et(r["event_date"]),
            "order_id": r["order_id"],
            "adv5": flip_first_order(r["is_first"]),
        })

    return {
        "csv_rows": csv_rows,
        "skipped_ours": skipped_ours,
        "cross_att": cross_att,
        "hashed": hashed,
    }


# --- Output ---------------------------------------------------------------

def write_csv(rows, target_dates, output_dir):
    now = datetime.now(ART_TZ)
    if len(target_dates) == 1:
        date_range = target_dates[0].strftime("%m_%d")
    else:
        date_range = f"{min(target_dates).strftime('%m_%d')}-{max(target_dates).strftime('%m_%d')}"
    filename = f"Vibe_without_clicks_{date_range}_{now.strftime('%Y%m%d')}.csv"
    filepath = os.path.join(output_dir, filename)
    fieldnames = ["offer_id", "affiliate_id", "event_id", "payout", "revenue",
                  "sale_amount", "unix_timestamp", "order_id", "adv5"]
    os.makedirs(output_dir, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"[Output] {filepath} ({len(rows)} rows)")
    return filepath


def build_slack_message(result, target_dates, brand_mapping):
    rows = result["csv_rows"]
    if len(target_dates) == 1:
        dr = target_dates[0].strftime("%m/%d")
    else:
        dr = f"{min(target_dates).strftime('%m/%d')}–{max(target_dates).strftime('%m/%d')}"

    total_revenue = sum(float(r["revenue"]) for r in rows)
    total_spend = sum(float(r["payout"]) for r in rows)

    lines = [
        f"*Vibe Conversion Sync — {dr}*",
        f"Uploaded: {len(rows)} conversions",
        f"Revenue: ${total_revenue:,.2f}",
        f"Spend: ${total_spend:,.2f}",
    ]

    brand_counts = Counter()
    brand_rev = defaultdict(float)
    brand_pay = defaultdict(float)
    for row in rows:
        for name, cfg in brand_mapping.items():
            if row["offer_id"] == cfg["offer_id"]:
                brand_counts[name] += 1
                brand_rev[name] += float(row["revenue"])
                brand_pay[name] += float(row["payout"])
                break
    if brand_counts:
        lines.append("")
        lines.append("*Per brand:*")
        for b in sorted(brand_counts):
            profit = brand_rev[b] - brand_pay[b]
            lines.append(f"• {b}: {brand_counts[b]} conv, profit ${profit:,.2f}")

    if result["cross_att"]:
        lines.append("")
        lines.append(f":rotating_light: *Cross-attribution — {len(result['cross_att'])} conversion(s) SKIPPED:*")
        brand_partners = defaultdict(lambda: {"count": 0, "partners": set()})
        for item in result["cross_att"]:
            entry = brand_partners[item["brand"]]
            entry["count"] += 1
            for (partner, _status), _c in item["partners"].items():
                entry["partners"].add(partner)
        for brand in sorted(brand_partners):
            entry = brand_partners[brand]
            partners_str = ", ".join(sorted(entry["partners"]))
            lines.append(f"• {brand}: {entry['count']} ({partners_str})")

    return "\n".join(lines)


# --- Main -----------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Vibe -> Everflow conversion sync.")
    p.add_argument("--upload-dir", default="./vibe upload",
                   help="Folder containing the 4 input CSVs (default: ./vibe upload)")
    p.add_argument("--output-dir", default="./vibe automation",
                   help="Folder to write the Everflow import CSV to (default: ./vibe automation)")
    p.add_argument("--affiliate-id", type=int, default=445,
                   help="Everflow affiliate ID for dedup + CSV output (default: 445)")
    return p.parse_args()


def run(upload_dir, output_dir, affiliate_id):
    target_dates = sorted(get_target_dates())
    print(f"[Dates] Target dates: {[d.isoformat() for d in target_dates]}")

    mapping_path = os.path.join(upload_dir, MAPPING_FILE)
    dashboard_path = os.path.join(upload_dir, DASHBOARD_FILE)
    spend_paths = sorted(glob.glob(os.path.join(upload_dir, SPEND_GLOB)))
    ef_paths = sorted(glob.glob(os.path.join(upload_dir, EF_EXPORT_GLOB)))

    if not os.path.exists(mapping_path):
        raise SystemExit(f"[FATAL] Missing mapping file: {mapping_path}")
    if not os.path.exists(dashboard_path):
        raise SystemExit(f"[FATAL] Missing dashboard file: {dashboard_path}")
    if not spend_paths:
        print(f"[Spend] WARNING: no files matching {SPEND_GLOB} in {upload_dir} — all payouts will be $0")
    if not ef_paths:
        print(f"[EF] WARNING: no files matching {EF_EXPORT_GLOB} — dedup will be skipped!")

    brand_mapping = load_brand_mapping(mapping_path)
    dashboard_rows, _skipped_brands = load_dashboard(dashboard_path, target_dates, brand_mapping)
    spend_map = load_spend(spend_paths, target_dates) if spend_paths else {}
    ef_map = load_ef_export(ef_paths) if ef_paths else {}

    result = build_output(dashboard_rows, ef_map, brand_mapping, spend_map, affiliate_id)
    csv_path = write_csv(result["csv_rows"], target_dates, output_dir)

    slack_msg = build_slack_message(result, target_dates, brand_mapping)
    print("\n[Slack Message Preview]")
    print(slack_msg)
    print("[/Slack Message Preview]")
    print(f"\n[CSV Path] {csv_path}")
    return csv_path, slack_msg


if __name__ == "__main__":
    args = parse_args()
    run(args.upload_dir, args.output_dir, args.affiliate_id)
