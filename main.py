"""
Blackcoffer - Data Extraction and AI Text Analytics
===================================================

End-to-end pipeline in ONE file:

    Step 1  collect_urls()      -> crawl insights.blackcoffer.com, save Input.xlsx
    Step 2  extract_articles()  -> download each article, save articles/<URL_ID>.txt
    Step 3  analyse_articles()  -> compute the 13 text variables
    Step 4  save Output.xlsx    -> same column order as "Output Data Structure.xlsx"

"""

import argparse
import re
import time
from pathlib import Path

import nltk
import pandas as pd
import requests
from bs4 import BeautifulSoup


# Settings
# ---------------------------------
BASE_URL = "https://insights.blackcoffer.com"
MAX_URLS = 650                      # assignment: 600 or more
INPUT_FILE = "Input.xlsx"
OUTPUT_FILE = "Output.xlsx"
ARTICLES_DIR = Path("articles")
STOPWORDS_DIR = Path("StopWords")
MASTER_DICT_DIR = Path("MasterDictionary")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
DELAY = 0.5                         # seconds between requests (be polite to the server)

# Output columns in the exact order of "Output Data Structure.xlsx"
OUTPUT_COLUMNS = [
    "URL_ID", "URL",
    "POSITIVE SCORE", "NEGATIVE SCORE", "POLARITY SCORE", "SUBJECTIVITY SCORE",
    "AVG SENTENCE LENGTH", "PERCENTAGE OF COMPLEX WORDS", "FOG INDEX",
    "AVG NUMBER OF WORDS PER SENTENCE", "COMPLEX WORD COUNT", "WORD COUNT",
    "SYLLABLE PER WORD", "PERSONAL PRONOUNS", "AVG WORD LENGTH",
]


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def get_page(url, retries=3):
    """Download a page. Returns response or None if it keeps failing."""
    for _ in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(2)
    return None


def download_nltk_data():
    """Download the NLTK data we need (only first time)."""
    for pkg in ["punkt", "punkt_tab", "stopwords"]:
        try:
            nltk.download(pkg, quiet=True)
        except Exception:
            pass


# --------------------------------------------------------------------------
# STEP 1 : collect article URLs
# --------------------------------------------------------------------------
def urls_from_wordpress_api(limit):
    """The site is WordPress, so its REST API lists posts (100 per page)."""
    urls, page = [], 1
    while len(urls) < limit:
        r = get_page(f"{BASE_URL}/wp-json/wp/v2/posts?per_page=100&page={page}&_fields=link")
        if r is None:                 # API closed or no more pages
            break
        try:
            posts = r.json()
        except ValueError:
            break
        if not posts:
            break
        urls += [p["link"] for p in posts]
        page += 1
        time.sleep(DELAY)
    return urls


def urls_from_sitemap(limit):
    """Backup method: read the sitemap files."""
    urls = []
    root = get_page(f"{BASE_URL}/sitemap_index.xml") or get_page(f"{BASE_URL}/sitemap.xml")
    if root is None:
        return urls
    soup = BeautifulSoup(root.text, "xml")
    sitemaps = [loc.text for loc in soup.find_all("loc")]
    # if sitemap_index: loop over child sitemaps, else the file itself has urls
    for sm in sitemaps:
        if sm.endswith(".xml") and "post" in sm:
            r = get_page(sm)
            if r:
                urls += [l.text for l in BeautifulSoup(r.text, "xml").find_all("loc")]
        if len(urls) >= limit:
            break
    return urls


def urls_from_pagination(limit):
    """Last backup: walk through the blog listing pages /page/1, /page/2 ..."""
    urls, page = [], 1
    while len(urls) < limit and page < 200:
        r = get_page(f"{BASE_URL}/page/{page}/")
        if r is None:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        for h in soup.select("h3 a, h2 a"):
            href = h.get("href", "")
            if href.startswith(BASE_URL) and href not in urls:
                urls.append(href)
        page += 1
        time.sleep(DELAY)
    return urls


def collect_urls():
    print("Step 1: collecting URLs ...")
    urls = urls_from_wordpress_api(MAX_URLS)
    if len(urls) < MAX_URLS:
        urls += urls_from_sitemap(MAX_URLS)
    if len(urls) < MAX_URLS:
        urls += urls_from_pagination(MAX_URLS)

    # remove duplicates, keep order, keep only real article links
    clean = []
    for u in urls:
        u = u.strip()
        if u.startswith(BASE_URL) and u.rstrip("/") != BASE_URL and u not in clean:
            clean.append(u)
    clean = clean[:MAX_URLS]

    if not clean:
        raise SystemExit("Could not collect any URL. Check your internet connection.")

    df = pd.DataFrame({"URL_ID": range(1, len(clean) + 1), "URL": clean})
    df.to_excel(INPUT_FILE, index=False)
    print(f"  saved {len(df)} urls to {INPUT_FILE}")
    return df


# --------------------------------------------------------------------------
# STEP 2 : extract article title + text
# --------------------------------------------------------------------------
def extract_text(html):
    """Return 'title + article body' only (no header, footer, sidebar)."""
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""

    # The site uses the 'td-post-content' class for the body; others are fallbacks.
    body = (soup.select_one("div.td-post-content")
            or soup.select_one("div.entry-content")
            or soup.find("article"))
    if body is None:
        return title, ""

    # throw away things that are not article text
    for tag in body.find_all(["script", "style", "noscript", "iframe", "form", "nav"]):
        tag.decompose()

    paragraphs = [p.get_text(" ", strip=True) for p in body.find_all(["p", "li", "h2", "h3", "h4"])]
    text = "\n".join(p for p in paragraphs if p)
    return title, text


def extract_articles(df):
    print("Step 2: extracting article text ...")
    ARTICLES_DIR.mkdir(exist_ok=True)
    failed = []
    for _, row in df.iterrows():
        file = ARTICLES_DIR / f"{row['URL_ID']}.txt"
        if file.exists() and file.stat().st_size > 0:      # already done, skip
            continue
        r = get_page(row["URL"])
        if r is None:
            failed.append(row["URL_ID"])
            continue
        title, text = extract_text(r.text)
        if not text:
            failed.append(row["URL_ID"])
            continue
        file.write_text(title + "\n" + text, encoding="utf-8")
        print(f"  saved {file}")
        time.sleep(DELAY)
    if failed:
        print(f"  could not extract these URL_IDs: {failed}")


# --------------------------------------------------------------------------
# STEP 3 : text analysis
# --------------------------------------------------------------------------
def read_word_file(path):
    """Read a word list. Handles odd encodings and 'WORD | comment' lines."""
    words = set()
    with open(path, encoding="latin-1") as f:
        for line in f:
            word = line.split("|")[0].strip().lower()
            if word:
                words.add(word)
    return words


def load_resources():
    """Load stop words, and positive/negative dictionaries."""
    stop_words = set()
    for file in STOPWORDS_DIR.rglob("*.txt"):
        stop_words |= read_word_file(file)
    try:
        from nltk.corpus import stopwords
        stop_words |= set(stopwords.words("english"))   # nltk stop words as per document
    except LookupError:
        print("  (nltk stopwords not available, using only the StopWords folder)")

    positive = read_word_file(next(MASTER_DICT_DIR.rglob("positive-words.txt")))
    negative = read_word_file(next(MASTER_DICT_DIR.rglob("negative-words.txt")))
    # only keep dictionary words which are NOT stop words
    positive -= stop_words
    negative -= stop_words
    return stop_words, positive, negative


def count_syllables(word):
    """Count vowel groups; words ending in 'es' / 'ed' lose one syllable."""
    word = word.lower()
    count = len(re.findall(r"[aeiouy]+", word))
    if word.endswith(("es", "ed")) and count > 1:
        count -= 1
    return max(count, 1)


def count_personal_pronouns(text):
    """I, we, my, ours, us  - but not the country 'US'."""
    matches = re.findall(r"\b(I|we|my|ours|us)\b", text, flags=re.IGNORECASE)
    # re.IGNORECASE would also match 'US', so remove that case here
    us_country = len(re.findall(r"\bUS\b", text))
    return len(matches) - us_country


def split_sentences(text):
    try:
        return nltk.sent_tokenize(text)
    except LookupError:
        return [s for s in re.split(r"[.!?]+", text) if s.strip()]


def split_words(text):
    """Tokens that contain only letters (this removes punctuation like ? ! , .)"""
    try:
        tokens = nltk.word_tokenize(text)
    except LookupError:
        tokens = re.findall(r"[A-Za-z']+", text)
    return [re.sub(r"[^A-Za-z]", "", t) for t in tokens if re.sub(r"[^A-Za-z]", "", t)]


def analyse_text(text, stop_words, positive, negative):
    """Return the 13 variables for one article."""
    sentences = split_sentences(text)
    all_words = split_words(text)
    # cleaned words = words without stop words
    words = [w.lower() for w in all_words if w.lower() not in stop_words]

    word_count = len(words)
    sentence_count = max(len(sentences), 1)

    # ---- sentiment ----
    positive_score = sum(1 for w in words if w in positive)
    negative_score = sum(1 for w in words if w in negative)
    polarity = (positive_score - negative_score) / ((positive_score + negative_score) + 0.000001)
    subjectivity = (positive_score + negative_score) / (word_count + 0.000001)

    # ---- readability ----
    syllables = [count_syllables(w) for w in words]
    complex_count = sum(1 for s in syllables if s > 2)
    avg_sentence_length = word_count / sentence_count
    pct_complex = complex_count / word_count if word_count else 0
    fog = 0.4 * (avg_sentence_length + pct_complex)

    # ---- other variables ----
    syllable_per_word = sum(syllables) / word_count if word_count else 0
    avg_word_length = sum(len(w) for w in words) / word_count if word_count else 0
    pronouns = count_personal_pronouns(text)

    return {
        "POSITIVE SCORE": positive_score,
        "NEGATIVE SCORE": negative_score,
        "POLARITY SCORE": polarity,
        "SUBJECTIVITY SCORE": subjectivity,
        "AVG SENTENCE LENGTH": avg_sentence_length,
        "PERCENTAGE OF COMPLEX WORDS": pct_complex,
        "FOG INDEX": fog,
        "AVG NUMBER OF WORDS PER SENTENCE": avg_sentence_length,
        "COMPLEX WORD COUNT": complex_count,
        "WORD COUNT": word_count,
        "SYLLABLE PER WORD": syllable_per_word,
        "PERSONAL PRONOUNS": pronouns,
        "AVG WORD LENGTH": avg_word_length,
    }


def analyse_articles(df):
    print("Step 3: analysing articles ...")
    stop_words, positive, negative = load_resources()
    print(f"  {len(stop_words)} stop words, {len(positive)} positive, {len(negative)} negative words")

    rows = []
    for _, row in df.iterrows():
        file = ARTICLES_DIR / f"{row['URL_ID']}.txt"
        result = {"URL_ID": row["URL_ID"], "URL": row["URL"]}
        if file.exists():
            text = file.read_text(encoding="utf-8")
            result.update(analyse_text(text, stop_words, positive, negative))
        # if the file is missing the columns stay empty (NaN)
        rows.append(result)

    out = pd.DataFrame(rows).reindex(columns=OUTPUT_COLUMNS)
    out = out.round(4)
    out.to_excel(OUTPUT_FILE, index=False)
    print(f"Step 4: saved {OUTPUT_FILE} ({len(out)} rows)")
    return out


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Blackcoffer text analysis pipeline")
    parser.add_argument("--skip-urls", action="store_true", help="use existing Input.xlsx")
    parser.add_argument("--skip-extract", action="store_true", help="use existing articles/ folder")
    args = parser.parse_args()

    download_nltk_data()

    if args.skip_urls:
        df = pd.read_excel(INPUT_FILE)
    else:
        df = collect_urls()

    if not args.skip_extract:
        extract_articles(df)

    analyse_articles(df)
    print("Done.")


if __name__ == "__main__":
    main()
