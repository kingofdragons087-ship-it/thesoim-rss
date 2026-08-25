hereimport re
import html
import hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://thesoim.github.io/w/"
OUTPUT_FILE = "feed.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ThesoimRSS/1.0)"
}


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def make_id(title, link):
    return hashlib.sha256(
        f"{title}|{link}".encode("utf-8")
    ).hexdigest()


def main():
    response = requests.get(
        SOURCE_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    official = soup.find(id="official")

    if official is None:
        print("WARNING: #official was not found.")
        return

    items = []

    for link_tag in official.find_all("a", href=True):
        link = urljoin(SOURCE_URL, link_tag["href"])
        title = clean_text(link_tag.get_text(" ", strip=True))

        if not title:
            continue

        if link.startswith("#"):
            continue

        item_id = make_id(title, link)

        items.append({
            "id": item_id,
            "title": title,
            "link": link,
        })

    unique = {}

    for item in items:
        unique[item["id"]] = item

    items = list(unique.values())

    now = datetime.now(timezone.utc)

    rss_items = []

    for item in items:
        rss_items.append(f"""
        <item>
            <title>{html.escape(item["title"])}</title>
            <link>{html.escape(item["link"])}</link>
            <guid isPermaLink="false">{item["id"]}</guid>
            <description>
                تعريب جديد من قسم التعريبات الرسمية في ذا سويم
            </description>
            <pubDate>{now.strftime("%a, %d %b %Y %H:%M:%S GMT")}</pubDate>
        </item>
        """)

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>ذا سويم - التعريبات الرسمية</title>
        <link>{SOURCE_URL}</link>
        <description>
            التعريبات الموجودة في قسم Official في موقع ذا سويم
        </description>
        <language>ar</language>
        <lastBuildDate>
            {now.strftime("%a, %d %b %Y %H:%M:%S GMT")}
        </lastBuildDate>

        {"".join(rss_items)}
    </channel>
</rss>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write(rss)

    print(f"RSS generated successfully: {len(items)} items")


if __name__ == "__main__":
    main()
