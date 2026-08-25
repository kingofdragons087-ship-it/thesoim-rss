import hashlib
import html
import json
from datetime import datetime, timezone

import requests


BASE_URL = "https://thesoim.github.io/w/"
GAMES_URL = BASE_URL + "games.json"
OFFICIAL_URL = BASE_URL + "official.json"

OUTPUT_FILE = "feed.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ThesoimRSS/1.0)"
}


def load_json(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def make_id(game, section):
    value = f"{section}:{game.get('slug', '')}"

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def escape(value):
    return html.escape(
        str(value or ""),
        quote=False
    )


def game_to_item(game, section):
    title = game.get("title", "تعريب جديد")
    slug = game.get("slug", "")

    link = f"{BASE_URL}{section}/{slug}.html"

    version = game.get("version", "")
    size = game.get("size", "")
    platform = game.get("platform", "Android")

    categories = game.get("categories") or []
    tags = game.get("tags") or []

    story = game.get("story", "")
    keywords = game.get("keywords", "")

    created_at = game.get("createdAt") or game.get("updatedAt") or 0

    try:
        timestamp = int(created_at) / 1000

        pub_date = datetime.fromtimestamp(
            timestamp,
            timezone.utc
        ).strftime("%a, %d %b %Y %H:%M:%S GMT")

    except Exception:
        pub_date = datetime.now(
            timezone.utc
        ).strftime("%a, %d %b %Y %H:%M:%S GMT")

    description = []

    if version:
        description.append(
            f"<b>الإصدار:</b> {escape(version)}"
        )

    if size:
        description.append(
            f"<b>الحجم:</b> {escape(size)}"
        )

    if platform:
        description.append(
            f"<b>المنصة:</b> {escape(platform)}"
        )

    if categories:
        description.append(
            f"<b>التصنيف:</b> {escape(', '.join(categories))}"
        )

    if tags:
        description.append(
            f"<b>الوسوم:</b> {escape(', '.join(tags))}"
        )

    if story:
        description.append(
            escape(story)
        )

    if keywords:
        description.append(
            f"<b>الكلمات المفتاحية:</b> {escape(keywords)}"
        )

    description.append(
        f'<a href="{html.escape(link, quote=True)}">صفحة التعريب</a>'
    )

    item_id = make_id(game, section)

    return f"""
    <item>
        <title>{escape(title)}</title>

        <link>{html.escape(link, quote=True)}</link>

        <guid isPermaLink="false">{item_id}</guid>

        <description><![CDATA[
            {"<br>".join(description)}
        ]]></description>

        <pubDate>{pub_date}</pubDate>

        <category>تعريب</category>

        <category>{escape(platform)}</category>
    </item>
    """


def main():

    print("Loading Thesoim data...")

    games = load_json(GAMES_URL)

    official = load_json(OFFICIAL_URL)

    print(
        f"games.json: {len(games)} items"
    )

    print(
        f"official.json: {len(official)} items"
    )

    items = []

    # جميع تعريبات المجتمع
    for game in games:

        if game.get("isHidden"):
            continue

        if not game.get("slug"):
            continue

        items.append(
            game_to_item(
                game,
                "games"
            )
        )

    # جميع التعريبات الرسمية
    for game in official:

        if game.get("isHidden"):
            continue

        if not game.get("slug"):
            continue

        items.append(
            game_to_item(
                game,
                "official"
            )
        )

    now = datetime.now(
        timezone.utc
    ).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>

<rss version="2.0">

    <channel>

        <title>تعريبات ذا سويم</title>

        <link>{BASE_URL}</link>

        <description>
            جميع تعريبات ألعاب الأندرويد من ذا سويم
        </description>

        <language>ar</language>

        <lastBuildDate>{now}</lastBuildDate>

        {"".join(items)}

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
        f"RSS generated successfully: {len(items)} items"
    )


if __name__ == "__main__":
    main()
