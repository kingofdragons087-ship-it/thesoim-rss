import hashlib
import html
import json
import mimetypes
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


def escape_attr(value):
    return html.escape(
        str(value or ""),
        quote=True
    )


def get_first_image(game):
    """
    يأخذ أول صورة من images[].

    أمثلة:
    "omori1.png"
    "image/omori1.png"
    "https://example.com/image.png"
    """

    images = game.get("images") or []

    if not isinstance(images, list) or not images:
        return ""

    first_image = str(images[0]).strip()

    if not first_image:
        return ""

    # إذا كانت الصورة رابطًا كاملًا
    if first_image.startswith("http://") or first_image.startswith("https://"):
        return first_image

    # إزالة / من البداية حتى لا يصبح الرابط //image
    first_image = first_image.lstrip("/")

    # إذا البيانات تحتوي image/ بالفعل
    if first_image.startswith("image/"):
        return BASE_URL + first_image

    # الصور الموجودة في مجلد image
    return BASE_URL + "image/" + first_image


def get_image_type(image_url):
    """
    تحديد MIME type حسب امتداد الصورة.
    """

    url = image_url.lower().split("?")[0]

    if url.endswith(".png"):
        return "image/png"

    if url.endswith(".jpg") or url.endswith(".jpeg"):
        return "image/jpeg"

    if url.endswith(".webp"):
        return "image/webp"

    if url.endswith(".gif"):
        return "image/gif"

    if url.endswith(".avif"):
        return "image/avif"

    return "image/png"


def get_pub_date(game):
    created_at = game.get("createdAt")

    if not created_at:
        created_at = game.get("updatedAt")

    try:
        timestamp = int(created_at) / 1000

        return datetime.fromtimestamp(
            timestamp,
            timezone.utc
        ).strftime("%a, %d %b %Y %H:%M:%S GMT")

    except Exception:
        return datetime.now(
            timezone.utc
        ).strftime("%a, %d %b %Y %H:%M:%S GMT")


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

    pub_date = get_pub_date(game)

    # ==========================================================
    # الصورة الأولى من images[]
    # ==========================================================

    image_url = get_first_image(game)
    image_type = get_image_type(image_url)

    description = []

    # ==========================================================
    # الصورة داخل description
    #
    # هذا مهم لأن بعض قارئات RSS تبحث عن <img>
    # داخل محتوى المقال نفسه.
    # ==========================================================

    if image_url:

        description.append(
            f'<img src="{escape_attr(image_url)}" '
            f'alt="{escape_attr(title)}" />'
        )

    # ==========================================================
    # معلومات اللعبة
    # ==========================================================

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
            f"<b>التصنيف:</b> "
            f"{escape(', '.join(map(str, categories)))}"
        )

    if tags:

        description.append(
            f"<b>الوسوم:</b> "
            f"{escape(', '.join(map(str, tags)))}"
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
        f'<a href="{escape_attr(link)}">صفحة التعريب</a>'
    )

    item_id = make_id(game, section)

    # ==========================================================
    # Media RSS
    #
    # MonitoRSS / قارئات RSS
    # ==========================================================

    media_html = ""

    if image_url:

        media_html = f"""
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

    # ==========================================================
    # RSS ITEM
    # ==========================================================

    return f"""
    <item>

        <title>{escape(title)}</title>

        <link>{escape_attr(link)}</link>

        <guid isPermaLink="false">{item_id}</guid>

        <description><![CDATA[
            {"<br>".join(description)}
        ]]></description>

        {media_html}

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

    # ==========================================================
    # تعريبات المجتمع
    # ==========================================================

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

    # ==========================================================
    # التعريبات الرسمية
    # ==========================================================

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

    # ==========================================================
    # ترتيب RSS حسب التاريخ
    # ==========================================================

    now = datetime.now(
        timezone.utc
    ).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )

    # ==========================================================
    # RSS
    # ==========================================================

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>

<rss version="2.0"
     xmlns:media="http://search.yahoo.com/mrss/">

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

    # ==========================================================
    # حفظ الملف
    # ==========================================================

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
