#!/usr/bin/env python3
import json, os, re, sys, hashlib, subprocess
from collections import Counter
from pathlib import Path

import fitz
import imagehash
import pytesseract
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "public" / "ads"
DATA_DIR = ROOT / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

SOURCES = [
    {
        "volume": 1,
        "url": "https://mattbockenstette.com/wp-content/uploads/2022/09/claude-hopkins-pages-1-2.pdf",
        "file": "/tmp/hopkins-1.pdf",
    },
    {
        "volume": 2,
        "url": "https://mattbockenstette.com/wp-content/uploads/2022/09/claude-hopkins-pages-2.pdf",
        "file": "/tmp/hopkins-2.pdf",
    },
    {
        "volume": 3,
        "url": "https://mattbockenstette.com/wp-content/uploads/2022/09/claude-hopkins-pages-3.pdf",
        "file": "/tmp/hopkins-3.pdf",
    },
]

# Campaign-level verification sources. These do not prove that every execution on a page
# was personally written by Hopkins; they establish that the named account/campaign is
# documented in Hopkins' work or reputable advertising-history sources.
BRANDS = [
    (r"pepsodent", "Pepsodent", [
        {"label":"Library of Congress — My Life in Advertising (Hopkins)","url":"https://www.loc.gov/item/27024090/"},
        {"label":"Made in Chicago Museum — Pepsodent history","url":"https://www.madeinchicagomuseum.com/single-post/pepsodent/"}
    ]),
    (r"palmolive", "Palmolive", [
        {"label":"Library of Congress — My Life in Advertising (Hopkins)","url":"https://www.loc.gov/item/27024090/"}
    ]),
    (r"quaker|puffed wheat|puffed rice", "Quaker Oats", [
        {"label":"Library of Congress — My Life in Advertising (Hopkins)","url":"https://www.loc.gov/item/27024090/"},
        {"label":"Smithsonian — Alexander Anderson and cereal shot from guns","url":"https://invention.si.edu/invention-stories/alexander-anderson-and-cereal-shot-guns"}
    ]),
    (r"goodyear", "Goodyear", [
        {"label":"Library of Congress — My Life in Advertising (Hopkins)","url":"https://www.loc.gov/item/27024090/"}
    ]),
    (r"schlitz", "Schlitz", [
        {"label":"Library of Congress — My Life in Advertising (Hopkins)","url":"https://www.loc.gov/item/27024090/"},
        {"label":"Advertising-history study — Hopkins and Schlitz","url":"https://historycooperative.org/journal/claude-hopkins-earnest-calkins-bissell-carpet-sweepers-and-the-birth-of-modern-advertising/"}
    ]),
    (r"liquozone|liquefied ozone", "Liquozone", [
        {"label":"Library of Congress — My Life in Advertising (Hopkins)","url":"https://www.loc.gov/item/27024090/"}
    ]),
    (r"van camp", "Van Camp's", [
        {"label":"Library of Congress — My Life in Advertising (Hopkins)","url":"https://www.loc.gov/item/27024090/"}
    ]),
    (r"dr\.?\s*shoop|shoop's", "Dr. Shoop", [
        {"label":"Library of Congress — My Life in Advertising (Hopkins)","url":"https://www.loc.gov/item/27024090/"}
    ]),
    (r"bissell", "Bissell", [
        {"label":"Advertising-history study — Bissell and Hopkins","url":"https://www.cambridge.org/core/journals/journal-of-the-gilded-age-and-progressive-era/article/abs/claude-hopkins-earnest-calkins-bissell-carpet-sweepers-and-the-birth-of-modern-advertising1/8F760E79B271A3A9A5EACECC1B32197C"}
    ]),
    (r"cotosuet|swift", "Swift / Cotosuet", [
        {"label":"Library of Congress — My Life in Advertising (Hopkins)","url":"https://www.loc.gov/item/27024090/"}
    ]),
    (r"chalmers", "Chalmers-Detroit", [
        {"label":"Automobile advertising research — Hopkins campaigns","url":"https://www.researchgate.net/publication/247576109_This_Astounding_Car_for_1500_The_Year_Automobile_Advertising_Came_of_Age"}
    ]),
    (r"hudson", "Hudson", [
        {"label":"Library of Congress — My Life in Advertising (Hopkins)","url":"https://www.loc.gov/item/27024090/"}
    ]),
    (r"\breo\b|reo the fifth", "REO", [
        {"label":"Automobile advertising research — Hopkins campaigns","url":"https://www.researchgate.net/publication/247576109_This_Astounding_Car_for_1500_The_Year_Automobile_Advertising_Came_of_Age"}
    ]),
    (r"overland|willys", "Willys-Overland", [
        {"label":"Automobile advertising research — Hopkins campaigns","url":"https://www.researchgate.net/publication/247576109_This_Astounding_Car_for_1500_The_Year_Automobile_Advertising_Came_of_Age"}
    ]),
    (r"studebaker", "Studebaker", [
        {"label":"Library of Congress — My Life in Advertising (Hopkins)","url":"https://www.loc.gov/item/27024090/"}
    ]),
    (r"mitchell", "Mitchell", [
        {"label":"Library of Congress — My Life in Advertising (Hopkins)","url":"https://www.loc.gov/item/27024090/"}
    ]),
    (r"racine", "Racine", [
        {"label":"Library of Congress — My Life in Advertising (Hopkins)","url":"https://www.loc.gov/item/27024090/"}
    ]),
]


def download(url, path):
    if Path(path).exists() and Path(path).stat().st_size > 1_000_000:
        return
    subprocess.run(["curl", "-L", "--fail", "--retry", "3", "--retry-delay", "2", "-o", path, url], check=True)


def clean_text(text):
    text = text.replace("\x00", " ")
    return re.sub(r"[ \t]+", " ", text)


def classify(text):
    low = text.lower()
    for pattern, brand, sources in BRANDS:
        if re.search(pattern, low, re.I):
            return brand, sources
    return "Unclassified", []


def detect_year(text):
    years = [int(x) for x in re.findall(r"\b(18[8-9]\d|19[0-2]\d)\b", text)]
    if not years:
        return None
    counts = Counter(years)
    return counts.most_common(1)[0][0]


def headline_from_ocr(text, brand):
    lines = []
    for raw in text.splitlines():
        s = re.sub(r"\s+", " ", raw).strip(" |—–-_=.")
        if 8 <= len(s) <= 115 and not re.fullmatch(r"[\d\W]+", s):
            lines.append(s)
    if not lines:
        return f"{brand} advertisement" if brand != "Unclassified" else "Archive advertisement"
    # Prefer early substantial lines; OCR often places the dominant headline first.
    for s in lines[:12]:
        if len(s.split()) >= 3:
            return s
    return lines[0]


def main():
    manifest = []
    seen_hashes = set()
    stats = {"source_pages": 0, "published_pages": 0, "duplicates": 0, "volumes": []}

    for src in SOURCES:
        download(src["url"], src["file"])
        doc = fitz.open(src["file"])
        stats["volumes"].append({"volume":src["volume"],"pages":len(doc),"url":src["url"]})
        stats["source_pages"] += len(doc)

        vol_dir = OUT_DIR / f"v{src['volume']}"
        vol_dir.mkdir(parents=True, exist_ok=True)

        for index, page in enumerate(doc):
            page_no = index + 1
            # Render first; image is the archival object.
            rect = page.rect
            scale = min(2.0, 1800 / max(rect.width, 1))
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.thumbnail((1800, 2400), Image.Resampling.LANCZOS)

            ph = str(imagehash.phash(img.resize((512,512))))
            if ph in seen_hashes:
                stats["duplicates"] += 1
                continue
            seen_hashes.add(ph)

            rel = f"public/ads/v{src['volume']}/page-{page_no:04d}.webp"
            out = ROOT / rel
            img.save(out, "WEBP", quality=70, method=6)

            embedded = clean_text(page.get_text("text") or "")
            if len(embedded.strip()) < 80:
                ocr_img = img.copy()
                ocr_img.thumbnail((1300,1800), Image.Resampling.LANCZOS)
                text = clean_text(pytesseract.image_to_string(ocr_img, config="--psm 6"))
            else:
                text = embedded

            brand, verification_sources = classify(text)
            year = detect_year(text)
            headline = headline_from_ocr(text, brand)
            item_id = f"v{src['volume']}-p{page_no:04d}"

            manifest.append({
                "id": item_id,
                "brand": brand,
                "year": year,
                "headline": headline,
                "product": brand if brand != "Unclassified" else "Historical advertisement",
                "image": "/" + rel.replace("public/", ""),
                "imageSource": src["url"] + f"#page={page_no}",
                "verificationSources": [
                    {"label":f"CopyLegends public-domain Hopkins vault — volume {src['volume']}, page {page_no}","url":src["url"]},
                    {"label":"CopyLegends vault index","url":"https://mattbockenstette.com/vault/"},
                    *verification_sources,
                ],
                "hook": "Not yet independently annotated.",
                "offer": "Not yet independently annotated.",
                "proof": "See the original scan.",
                "principles": [],
                "attribution": "medium",
                "dateConfidence": "medium" if year else "low",
                "metadataConfidence": "auto",
                "sourceVolume": src["volume"],
                "sourcePage": page_no,
                "sourceLabel": f"Claude Hopkins Collection, volume {src['volume']}, page {page_no}",
                "ocrExcerpt": text[:900],
                "note": "Bulk archive record. The exact scan provenance is verified to the named Claude Hopkins public-domain collection. Brand/year/headline are OCR-assisted and should be treated as provisional unless a separate verification source is shown."
            })
            stats["published_pages"] += 1
            if stats["published_pages"] % 25 == 0:
                print(f"published {stats['published_pages']} pages", flush=True)

    manifest.sort(key=lambda a: ((a.get("brand") or ""), a.get("year") or 9999, a["sourceVolume"], a["sourcePage"]))
    (DATA_DIR / "archive.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "archive-stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
