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

    data = response.json()

    if not isinstance(data, list):
        raise ValueError(f"Expected list from {url}")

    return data


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
    اختيار أول صورة من images[].

    يدعم:
    images: ["image1.png", "image2.png"]

    وكذلك:
    images: [{"url": "image1.png"}, ...]

    وإذا لم توجد images[] يستخدم الحقول البديلة.
    """

    images = game.get("images")

    # الحالة الطبيعية: images[]
    if isinstance(images, list):

        for image in images:

            if isinstance(image, str) and image.strip():
                return image.strip()

            if isinstance(image, dict):

                for key in (
                    "url",
                    "src",
                    "image",
                    "path"
                ):
                    value = image.get(key)

                    if isinstance(value, str) and value.strip():
                        return value.strip()

    # دعم لو images كانت نصًا بدل array
    if isinstance(images, str) and images.strip():
        return images.strip()

    # حقول بديلة احتياطية
    for key in (
        "image",
        "imageUrl",
        "image_url",
        "thumbnail",
        "cover",
        "coverImage",
        "cover_image"
    ):
        value = game.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def normalize_image_url(image):
    """
    تحويل مسار الصورة إلى URL كامل.
    """

    if not image:
        return ""

    image = str(image).strip()

    if image.startswith("http://") or image.startswith("https://"):
        return image

    if image.startswith("//"):
        return "https:" + image

    # رابط يبدأ بـ /
    if image.startswith("/"):
        return "https://thesoim.github.io" + image

    # الصور الموجودة عادة في /w/image/
    if image.startswith("image/"):
        return BASE_URL + image

    return BASE_URL + "image/" + image


def get_image_type(image_url):
    """
    تحديد MIME type للصورة.
    """

    mime_type, _ = mimetypes.guess_type(image_url)

    if mime_type and mime_type.startswith("image/"):
        return mime_type

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

    categories = game.get(
        "categories"
    ) or []

    tags = game.get(
        "tags"
    ) or []

    story = game.get(
        "story",
        ""
    )

    keywords = game.get(
        "keywords",
        ""
    )

    # ----------------------------------------
    # الصورة الأولى
    # ----------------------------------------

    image = get_first_image(game)

    image_url = normalize_image_url(image)

    image_type = get_image_type(
        image_url
    )

    # ----------------------------------------
    # الوصف
    # ----------------------------------------

    description = []

    # الصورة أول شيء
    #
    # هذا مهم لـ MonitoRSS و Discord
    # لأن بعض القارئات لا تعتمد على
    # media:content وحده.
    if image_url:

        description.append(
            f'<img src="{escape_attr(image_url)}" '
            f'alt="{escape_attr(title)}" />'
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
        f'<a href="{escape_attr(link)}">'
        f"صفحة التعريب"
        f"</a>"
    )

    description_html = "<br>".join(
        description
    )

    item_id = make_id(
        game,
        section
    )

    pub_date = get_pub_date(
        game
    )

    # ----------------------------------------
    # صورة RSS
    # ----------------------------------------

    media_block = ""

    if image_url:

        media_block = f"""
        <media:content
            url="{escape_attr(image_url)}"
            medium="image"
            type="{escape_attr(image_type)}"
        />

        <media:thumbnail
            url="{escape_attr(image_url)}"
        />

        <enclosure
            url="{escape_attr(image_url)}"
            type="{escape_attr(image_type)}"
            length="0"
        />

        <image>
            <url>{escape(image_url)}</url>
            <title>{escape(title)}</title>
            <link>{escape(link)}</link>
        </image>
        """

    # ----------------------------------------
    # RSS item
    # ----------------------------------------

    return f"""
    <item>

        <title>{escape(title)}</title>

        <link>{escape(link)}</link>

        <guid isPermaLink="false">
            {item_id}
        </guid>

        <description><![CDATA[
            {description_html}
        ]]></description>

        {media_block}

        <pubDate>{pub_date}</pubDate>

        <category>تعريب</category>

        <category>{escape(platform)}</category>

    </item>
    """


def main():

    print("Loading Thesoim data...")

    games = load_json(
        GAMES_URL
    )

    official = load_json(
        OFFICIAL_URL
    )

    print(
        f"games.json: {len(games)} items"
    )

    print(
        f"official.json: {len(official)} items"
    )

    items = []

    images_found = 0
    images_missing = 0

    # ----------------------------------------
    # تعريبات المجتمع
    # ----------------------------------------

    for game in games:

        if game.get("isHidden"):
            continue

        if not game.get("slug"):
            continue

        image = normalize_image_url(
            get_first_image(game)
        )

        if image:
            images_found += 1
        else:
            images_missing += 1

        items.append(
            game_to_item(
                game,
                "games"
            )
        )

    # ----------------------------------------
    # التعريبات الرسمية
    # ----------------------------------------

    for game in official:

        if game.get("isHidden"):
            continue

        if not game.get("slug"):
            continue

        image = normalize_image_url(
            get_first_image(game)
        )

        if image:
            images_found += 1
        else:
            images_missing += 1

        items.append(
            game_to_item(
                game,
                "official"
            )
        )

    # ----------------------------------------
    # تاريخ بناء RSS
    # ----------------------------------------

    now = datetime.now(
        timezone.utc
    ).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )

    # ----------------------------------------
    # RSS
    # ----------------------------------------

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>

<rss version="2.0"
     xmlns:media="http://search.yahoo.com/mrss/"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">

    <channel>

        <title>تعريبات ذا سويم</title>

        <link>{BASE_URL}</link>

        <description>
            جميع تعريبات ألعاب الأندرويد من ذا سويم
        </description>

        <language>ar</language>

        <lastBuildDate>{now}</lastBuildDate>

        <generator>Thesoim RSS Generator</generator>

        {"".join(items)}

    </channel>

</rss>
"""

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            rss
        )

    print(
        f"RSS generated successfully: "
        f"{len(items)} items"
    )

    print(
        f"Images found: {images_found}"
    )

    print(
        f"Images missing: {images_missing}"
    )


if __name__ == "__main__":
    main()
