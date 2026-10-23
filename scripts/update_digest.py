import json, re, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

TZ = timezone(timedelta(hours=8))
now = datetime.now(TZ)
today = now.strftime("%Y-%m-%d")
cutoff = now - timedelta(days=60)

# Search terms are discovery queries, not proof that a policy or vacancy is official.
queries = {
    "global": [
        "world news international economy technology when:30d",
        "global agriculture food security climate when:30d",
    ],
    "plant": [
        "plant protection entomology pesticide resistance biological control research when:30d",
        "plant pathology crop pests pesticide research when:30d",
    ],
    "visa": [
        "site:immi.homeaffairs.gov.au visa skilled migration update",
        "site:immigration.govt.nz work visa policy update",
        "site:uscis.gov employment visa international workers update",
    ],
    "jobs": [
        "agrochemical crop science plant protection jobs international when:30d",
        "pesticide research development jobs agriculture international when:30d",
        "agrochemical careers official company jobs",
    ],
}

def clean(s):
    return re.sub(r"<[^>]+>", " ", s or "").replace("&amp;", "&").replace("&quot;", '"').strip()

all_by_category = {}
for cat, terms in queries.items():
    candidates = []
    for term in terms:
        url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(term) + "&hl=en-US&gl=US&ceid=US:en"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 plant-protection-intel/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                root = ET.fromstring(resp.read())
            for item in root.findall(".//item"):
                title = clean(item.findtext("title"))
                link = item.findtext("link") or ""
                desc = clean(item.findtext("description"))
                source = clean(item.findtext("source"))
                if not title or not link:
                    continue
                pubdate = ""
                parsed = None
                try:
                    parsed = parsedate_to_datetime(item.findtext("pubDate")).astimezone(TZ)
                    pubdate = parsed.strftime("%Y-%m-%d")
                except Exception:
                    pass
                # For dated results, skip material older than 60 days.
                if parsed and parsed < cutoff:
                    continue
                candidates.append({
                    "category": cat,
                    "title": title,
                    "url": link,
                    "summary": desc[:360],
                    "source": source or "Google News RSS",
                    "date": pubdate,
                })
        except Exception as e:
            print("RSS failed:", term, str(e))
    seen = set()
    deduped = []
    for x in candidates:
        key = x["title"].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(x)
    # Keep each category represented; do not let global news crowd out visa/jobs/research.
    all_by_category[cat] = deduped[:25]

items = []
for cat in queries:
    items.extend(all_by_category.get(cat, []))
items.sort(key=lambda x: x.get("date", ""), reverse=True)

data = {
    "date": today,
    "updated": now.strftime("%Y-%m-%d %H:%M") + " CST",
    "items": items,
    "note": "Automated RSS discovery, limited to the latest 60 days where dates are available. News is a lead, not verification. Confirm visa rules on government websites and vacancies on the employer's official careers page."
}
Path("data").mkdir(exist_ok=True)
Path("data/current.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
Path("data/archive").mkdir(exist_ok=True)
Path(f"data/archive/{today}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
idx = Path("data/archive/index.json")
try:
    dates = json.loads(idx.read_text(encoding="utf-8"))
except Exception:
    dates = []
if today not in dates:
    dates.append(today)
idx.write_text(json.dumps(sorted(dates, reverse=True), ensure_ascii=False, indent=2), encoding="utf-8")
print("Wrote", len(items), "items for", today, "by category:", {k: len(v) for k, v in all_by_category.items()})
