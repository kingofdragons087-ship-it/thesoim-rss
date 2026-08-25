import re
import html
import hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://thesoim.github.io/w/"
OUTPUT_FILE = "feed.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ThesoimRSS/1.0)"
}


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def make_id(link):
    return hashlib.sha256(link.encode("utf-8")).hexdigest()


def get_page(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


def extract_game_data(url):
    soup = get_page(url)

    title = ""

    h1 = soup.find("h1")

    if h1:
        title = clean_text(h1.get_text(" ", strip=True))

    if not title:
        return None

    text = clean_text(soup.get_text(" ", strip=True))

    version = ""

    version_match = re.search(
        r"الإصدار\s+(v[0-9A-Za-z._-]+)",
        text
    )

    if version_match:
        version = version_match.group(1)

    size = ""

    size_match = re.search(
        r"الحجم\s+([0-9.]+\s*(?:MB|GB))",
        text,
        re.IGNORECASE
    )

    if size_match:
        size = size_match.group(1)

    platform = ""

    platform_match = re.search(
        r"المنصة\s+(Android|iOS|Windows|PC)",
        text,
        re.IGNORECASE
    )

    if platform_match:
        platform = platform_match.group(1)

    category = ""

    category_match = re.search(
        r"التصنيف\s+(.+?)\s+وقت اللعب",
        text
    )

    if category_match:
        category = clean_text(category_match.group(1))

    description = ""

    story = soup.find(
        lambda tag: tag.name in ["h2", "h3"]
        and clean_text(tag.get_text()) == "القصة"
    )

    if story:
        next_element = story.find_next()

        if next_element:
            description = clean_text(
                next_element.get_text(" ", strip=True)
            )

    return {
        "title": title,
        "link": url,
        "version": version,
        "size": size,
        "platform": platform,
        "category": category,
        "description": description
    }


def main():

    print("Opening Thesoim...")

    soup = get_page(BASE_URL)

    game_links = set()

    # البحث عن جميع صفحات الألعاب
    for a in soup.find_all("a", href=True):

        href = a["href"]

        full_url = urljoin(BASE_URL, href)

        if "/games/" in full_url and full_url.endswith(".html"):
            game_links.add(full_url)

    print(f"Found {len(game_links)} game links")

    games = []

    for url in sorted(game_links):

        try:

            print(f"Reading: {url}")

            game = extract_game_data(url)

            if game:
                games.append(game)

        except Exception as error:

            print(
                f"Failed to read {url}: {error}"
            )

    print(f"Successfully extracted: {len(games)} games")

    now = datetime.now(timezone.utc)

    rss_items = []

    for game in games:

        description_parts = []

        if game["version"]:
            description_parts.append(
                f"الإصدار: {game['version']}"
            )

        if game["size"]:
            description_parts.append(
                f"الحجم: {game['size']}"
            )

        if game["platform"]:
            description_parts.append(
                f"المنصة: {game['platform']}"
            )

        if game["category"]:
            description_parts.append(
                f"التصنيف: {game['category']}"
            )

        if game["description"]:
            description_parts.append(
                game["description"]
            )

        description = "<br>".join(
            html.escape(x)
            for x in description_parts
        )

        item_id = make_id(game["link"])

        rss_items.append(
            f"""
        <item>
            <title>{html.escape(game["title"])}</title>

            <link>{html.escape(game["link"])}</link>

            <guid isPermaLink="false">
                {item_id}
            </guid>

            <description>
                <![CDATA[
                {description}
                ]]>
            </description>

            <pubDate>
                {now.strftime("%a, %d %b %Y %H:%M:%S GMT")}
            </pubDate>
        </item>
        """
        )

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>

<rss version="2.0">

    <channel>

        <title>تعريبات ذا سويم</title>

        <link>{BASE_URL}</link>

        <description>
            جميع تعريبات ألعاب Android من ذا سويم
        </description>

        <language>ar</language>

        <lastBuildDate>
            {now.strftime("%a, %d %b %Y %H:%M:%S GMT")}
        </lastBuildDate>

        {"".join(rss_items)}

    </channel>

</rss>
"""

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(rss)

    print(
        f"RSS generated successfully: {len(games)} items"
    )


if __name__ == "__main__":
    main()
