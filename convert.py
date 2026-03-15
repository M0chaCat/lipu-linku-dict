import tomllib
import html
import subprocess
from pathlib import Path
from git import Repo

# URL of the repository
repo_url = "https://github.com/lipu-linku/sona.git"

# Clone the repo
Repo.clone_from(repo_url, "./sona/")

WORDS_FILE = Path("./sona/words/source/definition.toml")
METADATA_DIR = Path("./sona/words/metadata/")

OUTPUT_XML = "Dictionary.xml"
IMAGE_DIR = Path("OtherResources/Images")

IMAGE_DIR.mkdir(exist_ok=True)

def normalize_id(word: str) -> str:
    return word.replace(" ", "_").replace("'", "").lower()


def load_metadata(word):
    path = METADATA_DIR / f"{word}.toml"
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def download_with_curl(url: str, dest: Path) -> bool:
    if dest.exists():
        return True
    try:
        subprocess.run(
            ["curl", "-L", "-o", str(dest), url],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to download {url}")
        return False


def download_images(words):
    image_map = {}
    for word in words:
        meta = load_metadata(word)
        if not meta:
            continue
        url = meta.get("image") or meta.get("svg")
        if not url:
            continue
        ext = url.split(".")[-1].split("?")[0]
        filename = f"{normalize_id(word)}.{ext}"
        dest = IMAGE_DIR / filename
        if download_with_curl(url, dest):
            image_map[word] = f"Images/{filename}"
    return image_map


def make_image_section(word, image_map):
    if word not in image_map:
        return ""
    img = html.escape(image_map[word])
    return f'''
<span class="picture">
<img src="{img}" alt="{html.escape(word)}"/>
</span>
'''


def make_meta_info(meta):
    parts = []
    if meta.get("author"):
        authors = ", ".join(meta["author"])
        parts.append(f'<div><b>Author:</b> {html.escape(authors)}</div>')
    if meta.get("book"):
        parts.append(f'<div><b>Book:</b> {html.escape(meta["book"])}</div>')
    if meta.get("coined_era"):
        parts.append(f'<div><b>Era:</b> {html.escape(meta["coined_era"])}</div>')
    ety = meta.get("translations", {}).get("etymology")
    if ety:
        parts.append(f'<div><b>Etymology:</b> {html.escape(ety)}</div>')
    return "\n".join(parts)


def make_see_also(meta):
    words = meta.get("see_also")
    if not words:
        return ""
    links = []
    for w in words:
        wid = normalize_id(w)
        links.append(f'<a href="x-dictionary:r:{wid}">{html.escape(w)}</a>')
    return "<div><b>See also: </b> " + ", ".join(links) + "</div>"


def make_entry(word, definition, image_map):
    meta = load_metadata(word)

    entry_id = normalize_id(word)
    word_e = html.escape(word)

    # Get the definition from metadata or fallback
    definition_text = meta.get("translations", {}).get("definition", definition)

    # Split by semicolon, strip whitespace
    definition_items = [item.strip() for item in definition_text.split(";") if item.strip()]

    # Each item becomes a separate div containing a ul wrapping a div
    definition_html = "\n".join(
        f"<div>\n    <ul>\n        <div>{html.escape(item)}</div>\n    </ul>\n</div>"
        for item in definition_items
    )

    image_section = make_image_section(word, image_map)
    meta_info = make_meta_info(meta)
    see_also = make_see_also(meta)

    return f"""
<d:entry id="{entry_id}" d:title="{word_e}">
    <d:index d:value="{word_e}"/>
    <h1>{word_e}</h1>

    {image_section}

    {definition_html}

    {meta_info}

    {see_also}

</d:entry>
""".strip()


def main():
    with open(WORDS_FILE, "rb") as f:
        words = tomllib.load(f)

    print("Downloading images via curl...")
    image_map = download_images(words)

    entries = [make_entry(word, definition, image_map) for word, definition in words.items()]

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<d:dictionary xmlns="http://www.w3.org/1999/xhtml"
              xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng">

{chr(10).join(entries)}

</d:dictionary>
'''

    Path(OUTPUT_XML).write_text(xml, encoding="utf-8")
    print("pona! Dictionary.xml pini, nja!")


if __name__ == "__main__":
    main()
