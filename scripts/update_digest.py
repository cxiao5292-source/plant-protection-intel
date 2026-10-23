import json, re, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

TZ = timezone(timedelta(hours=8))
now = datetime.now(TZ)
today = now.strftime("%Y-%m-%d")
cutoff = now - timedelta(days=45)

# Google News RSS is used only for discovery. Each item must still be checked at its original source.
queries = {
    "global": [
        "world international economy technology climate news when:14d",
        "global food security agriculture geopolitics news when:14d",
    ],
    "plant": [
        "plant protection entomology pesticide resistance biological control research when:30d",
        "plant pathology crop pests pesticide research university extension when:30d",
    ],
    "visa": [
        "site:immi.homeaffairs.gov.au visa skilled migration",
        "site:immigration.govt.nz work visa policy",
        "site:uscis.gov employment visa policy",
        "site:gov.uk/browse/visas-immigration work visa",
        "site:canada.ca immigration work permit",
    ],
    "jobs": [
        "site:careers.syngenta.com crop protection jobs",
        "site:jobs.corteva.com research development agriculture jobs",
        "site:careers.basf.com agricultural solutions jobs",
        "site:careers.bayer.com crop science jobs",
        "agrochemical crop protection research development jobs international when:14d",
    ],
}

def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\\s+", " ", s).replace("&amp;", "&").replace("&quot;", '"').strip()

def source_level(source, url, category):
    host = urllib.parse.urlparse(url).netloc.lower()
    s = (source or "").lower()
    if category == "visa" and (host.endswith(".gov") or ".gov." in host or "immigration new zealand" in s):
        return "政府/官方来源"
    if category == "jobs" and ("careers." in host or "jobs." in host or "workday" in host or "greenhouse.io" in host or "lever.co" in host):
        return "雇主/招聘平台线索，需核实"
    if any(k in s for k in ["university", "state of ", "department of", "extension", "government", ".gov"]):
        return "机构来源"
    return "媒体/聚合线索，需核实"

def relevant(cat, title, source):
    text = (title + " " + source).lower()
    if cat == "plant":
        return any(k in text for k in ["plant", "crop", "pest", "patholog", "insect", "fung", "pesticide", "herbicide", "fungicide", "biological control", "agriculture", "agronom", "resistance"])
    if cat == "visa":
        return any(k in text for k in ["visa", "immigration", "work permit", "skilled migration", "residence", "work rights"])
    if cat == "jobs":
        return any(k in text for k in ["job", "career", "vacanc", "hiring", "recruit", "position", "research and development", "research & development", "crop protection", "agricultural solutions"])
    return True

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
                if not title or not link or not relevant(cat, title, source):
                    continue
                parsed = None
                try:
                    raw_date = item.findtext("pubDate")
                    parsed = parsedate_to_datetime(raw_date).astimezone(TZ) if raw_date else None
                except Exception:
                    pass
                # Strict freshness: exclude undated items and items older than 45 days.
                if not parsed or parsed < cutoff or parsed > now + timedelta(days=1):
                    continue
                candidates.append({
                    "category": cat,
                    "title": title,
                    "url": link,
                    "summary": desc[:360],
                    "source": source or "Google News RSS",
                    "date": parsed.strftime("%Y-%m-%d"),
                    "source_level": source_level(source, link, cat),
                    "verification": "待打开原文核实",
                })
        except Exception as e:
            print("RSS failed:", term, str(e))
    seen = set()
    deduped = []
    for x in sorted(candidates, key=lambda x: x["date"], reverse=True):
        key = re.sub(r"[^a-z0-9]+", "", x["title"].lower())
        if key and key not in seen:
            seen.add(key)
            deduped.append(x)
    all_by_category[cat] = deduped[:20]

# Remove exact duplicate headlines across categories, retaining the most relevant first category.
items, seen_titles = [], set()
for cat in ("visa", "jobs", "plant", "global"):
    for x in all_by_category.get(cat, []):
        key = re.sub(r"[^a-z0-9]+", "", x["title"].lower())
        if key not in seen_titles:
            seen_titles.add(key)
            items.append(x)
items.sort(key=lambda x: x["date"], reverse=True)

data = {
    "date": today,
    "updated": now.strftime("%Y-%m-%d %H:%M") + " CST",
    "items": items,
    "counts": {cat: sum(1 for x in items if x["category"] == cat) for cat in queries},
    "note": "自动发现的公开 RSS 线索，不等同于事实核验。签证以政府官网政策页面为准；岗位必须打开雇主招聘官网确认是否仍在招聘、地点、签证担保及截止日期。没有日期的结果会被过滤。"
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
print("Wrote", len(items), "dated items for", today, "by category:", data["counts"])
if not items:
    print("WARNING: no dated items collected; investigate RSS availability before treating this run as successful.")
