import hashlib
import html
from datetime import datetime, timezone
from urllib.parse import urlparse

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


def escape_attr(value):
    return html.escape(
        str(value or ""),
        quote=True
    )


def get_first_image(game):
    """
    يأخذ أول صورة من images[].

    يدعم:
    [
        "https://example.com/image.png"
    ]

    وكذلك:
    [
        {
            "url": "https://example.com/image.png"
        }
    ]
    """

    images = game.get("images") or []

    if not isinstance(images, list):
        return ""

    for image in images:

        # images: ["url"]
        if isinstance(image, str):
            image = image.strip()

            if image:
                return image

        # images: [{"url": "..."}]
        if isinstance(image, dict):

            image_url = (
                image.get("url")
                or image.get("src")
                or image.get("image")
                or image.get("imageUrl")
            )

            if image_url:
                return str(image_url).strip()

    return ""


def get_image_type(image_url):
    """
    يحدد MIME type للصورة من امتداد الرابط.
    """

    if not image_url:
        return "image/jpeg"

    path = urlparse(image_url).path.lower()

    if path.endswith(".png"):
        return "image/png"

    if path.endswith(".webp"):
        return "image/webp"

    if path.endswith(".gif"):
        return "image/gif"

    if path.endswith(".jpg"):
        return "image/jpeg"

    if path.endswith(".jpeg"):
        return "image/jpeg"

    return "image/jpeg"


def get_pub_date(game):
    created_at = (
        game.get("createdAt")
        or game.get("updatedAt")
        or 0
    )

    try:
        timestamp = int(created_at) / 1000

        return datetime.fromtimestamp(
            timestamp,
            timezone.utc
        ).strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )

    except Exception:

        return datetime.now(
            timezone.utc
        ).strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )


def game_to_item(game, section):

    title = game.get(
        "title",
        "تعريب جديد"
    )

    slug = game.get(
        "slug",
        ""
    )

    link = (
        f"{BASE_URL}"
        f"{section}/"
        f"{slug}.html"
    )

    version = game.get(
        "version",
        ""
    )

    size = game.get(
        "size",
        ""
    )

    platform = game.get(
        "platform",
        "Android"
    )

    categories = (
        game.get("categories")
        or []
    )

    tags = (
        game.get("tags")
        or []
    )

    story = game.get(
        "story",
        ""
    )

    keywords = game.get(
        "keywords",
        ""
    )

    image_url = get_first_image(game)

    image_type = get_image_type(
        image_url
    )

    pub_date = get_pub_date(
        game
    )

    item_id = make_id(
        game,
        section
    )

    description = []

    # الصورة أولاً
    if image_url:

        description.append(
            f"""
            <p>
                <img
                    src="{escape_attr(image_url)}"
                    alt="{escape_attr(title)}"
                />
            </p>
            """
        )

    if version:

        description.append(
            f"<b>الإصدار:</b> "
            f"{escape(version)}"
        )

    if size:

        description.append(
            f"<b>الحجم:</b> "
            f"{escape(size)}"
        )

    if platform:

        description.append(
            f"<b>المنصة:</b> "
            f"{escape(platform)}"
        )

    if categories:

        description.append(
            f"<b>التصنيف:</b> "
            f"{escape(', '.join(categories))}"
        )

    if tags:

        description.append(
            f"<b>الوسوم:</b> "
            f"{escape(', '.join(tags))}"
        )

    if story:

        description.append(
            escape(story)
        )

    if keywords:

        description.append(
            f"<b>الكلمات المفتاحية:</b> "
            f"{escape(keywords)}"
        )

    description.append(
        f"""
        <p>
            <a href="{escape_attr(link)}">
                صفحة التعريب
            </a>
        </p>
        """
    )

    description_html = "<br>".join(
        description
    )

    # عناصر الصور الخاصة بقارئات RSS و Discord
    image_block = ""

    if image_url:

        image_block = f"""
        <media:content
            url="{escape_attr(image_url)}"
            medium="image"
            type="{image_type}"
        />

        <media:thumbnail
            url="{escape_attr(image_url)}"
        />

        <enclosure
            url="{escape_attr(image_url)}"
            type="{image_type}"
            length="1"
        />
        """

    return f"""
    <item>

        <title>{escape(title)}</title>

        <link>{escape_attr(link)}</link>

        <guid isPermaLink="false">
            {item_id}
        </guid>

        <description><![CDATA[
            {description_html}
        ]]></description>

        {image_block}

        <pubDate>{pub_date}</pubDate>

        <category>تعريب</category>

        <category>
            {escape(platform)}
        </category>

    </item>
    """


def main():

    print(
        "Loading Thesoim data..."
    )

    games = load_json(
        GAMES_URL
    )

    official = load_json(
        OFFICIAL_URL
    )

    print(
        f"games.json: "
        f"{len(games)} items"
    )

    print(
        f"official.json: "
        f"{len(official)} items"
    )

    items = []

    # ==========================
    # تعريبات المجتمع
    # ==========================

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

    # ==========================
    # التعريبات الرسمية
    # ==========================

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

<rss
    version="2.0"
    xmlns:media="http://search.yahoo.com/mrss/"
>

    <channel>

        <title>تعريبات ذا سويم</title>

        <link>
            {BASE_URL}
        </link>

        <description>
            جميع تعريبات ألعاب الأندرويد من ذا سويم
        </description>

        <language>ar</language>

        <lastBuildDate>
            {now}
        </lastBuildDate>

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
        f"RSS generated successfully: "
        f"{len(items)} items"
    )


if __name__ == "__main__":
    main()
