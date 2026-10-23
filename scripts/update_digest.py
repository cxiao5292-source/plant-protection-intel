import json, os, re, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
TZ=timezone(timedelta(hours=8)); now=datetime.now(TZ); today=now.strftime("%Y-%m-%d")
queries={
"global":["world news international economy technology","global agriculture food security climate"],
"plant":["plant protection entomology pesticide resistance biological control research","plant pathology crop pests pesticide research"],
"visa":["Australia immigration skilled visa official policy","New Zealand immigration work visa policy","United States work visa sponsorship international graduates"],
"jobs":["agrochemical crop science plant protection jobs international","pesticide research development jobs agriculture international"]}
out=[]
def clean(s):
 return re.sub(r"<[^>]+>"," ",s or "").replace("&amp;","&").replace("&quot;",'"').strip()
for cat,terms in queries.items():
 for term in terms:
  url="https://news.google.com/rss/search?q="+urllib.parse.quote(term)+"&hl=en-US&gl=US&ceid=US:en"
  try:
   req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 plant-protection-intel/1.0"})
   with urllib.request.urlopen(req,timeout=20) as resp: root=ET.fromstring(resp.read())
   for item in root.findall(".//item"):
    title=clean(item.findtext("title")); link=item.findtext("link") or ""; desc=clean(item.findtext("description")); source=clean(item.findtext("source"))
    if not title or not link: continue
    date=""
    try: date=parsedate_to_datetime(item.findtext("pubDate")).astimezone(TZ).strftime("%Y-%m-%d")
    except Exception: pass
    out.append({"category":cat,"title":title,"url":link,"summary":desc[:360],"source":source or "Google News RSS","date":date})
  except Exception as e: print("RSS failed:",term,str(e))
seen=set(); unique=[]
for x in out:
 key=x["title"].lower()
 if key not in seen: seen.add(key); unique.append(x)
unique=unique[:100]
data={"date":today,"updated":now.strftime("%Y-%m-%d %H:%M")+" CST","items":unique,"note":"RSS discovery only; verify policy and vacancies at original official sources."}
Path("data").mkdir(exist_ok=True)
Path("data/current.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
Path("data/archive").mkdir(exist_ok=True)
Path(f"data/archive/{today}.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
idx=Path("data/archive/index.json")
try: dates=json.loads(idx.read_text(encoding="utf-8"))
except Exception: dates=[]
if today not in dates: dates.append(today)
idx.write_text(json.dumps(sorted(dates,reverse=True),ensure_ascii=False,indent=2),encoding="utf-8")
print("Wrote",len(unique),"items for",today)
import urllib.parse
