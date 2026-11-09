# Blackcoffer – Data Extraction and Text Analysis

A Python project built for the **Blackcoffer Data Analysis Assignment**. It collects articles from the Blackcoffer Insights website, extracts their text, performs sentiment and readability analysis, and exports the results to a structured Excel file.

## Overview

- Collects article URLs using the WordPress REST API, with sitemap and pagination as fallbacks.
- Extracts only the article title and body using Requests and BeautifulSoup.
- Cleans text using NLTK and the assignment's stop-word lists.
- Calculates sentiment and readability variables from `Text Analysis.docx`.
- Saves results in `Output.xlsx` in the same column order as `Output Data Structure.xlsx`.

## Project Workflow

```text
        Blackcoffer Insights Website
                    |
                    v
          URL Collection
       (WordPress REST API)
                    |
          Fallback: Sitemap
          and Pagination
                    |
                    v
              Input.xlsx
            (URL_ID, URL)
                    |
                    v
           Article Extraction
          (Requests + BeautifulSoup)
                    |
                    v
             Text Cleaning
        (Tokenization, Stop Words,
          Punctuation Removal)
                    |
                    v
            Text Analysis
          /              \
         v                v
   Sentiment Analysis   Readability Analysis
         \                /
          \              /
                    |
                    v
               Output.xlsx
          (13 Analytical Variables)
```

## Technical Approach

### 1. URL Collection

The target website is built on WordPress, so the script first reads article links from the REST API:

`/wp-json/wp/v2/posts`

If the API is unavailable, it tries the sitemap, and then the paginated listing pages (`/page/N/`).

The collected URLs are deduplicated, limited to 650, and saved to `Input.xlsx` with the columns `URL_ID` and `URL`.

### 2. Article Extraction

- **Requests** downloads each article page.
- **BeautifulSoup** (`html.parser`) reads the HTML.
- The title comes from the `<h1>` element and the body from `div.td-post-content`.
- Headers, footers, sidebars, navigation and scripts are ignored.

Each article is saved as `articles/<URL_ID>.txt`, so it is not downloaded again on the next run.

### 3. Text Cleaning and Analysis

**Cleaning**
- Load stop words from every file in `StopWords/` and add the NLTK English stop words.
- Load the positive and negative dictionaries from `MasterDictionary/` and remove any stop words from them.
- Tokenize the text with NLTK, then remove punctuation and stop words.

**Sentiment analysis:** Positive Score, Negative Score, Polarity Score, Subjectivity Score.

**Readability analysis:** Average Sentence Length, Percentage of Complex Words, Fog Index, Average Number of Words per Sentence, Complex Word Count, Word Count, Syllables per Word, Personal Pronouns, Average Word Length.

### 4. Output Generation

Results are written to `Output.xlsx`. If an article cannot be downloaded, its row is kept with empty values. No numbers are made up.

---

## Variables and Calculation Formulas

| Variable | Calculation |
|---|---|
| Positive Score | Number of positive dictionary matches |
| Negative Score | Number of negative dictionary matches |
| Polarity Score | (Positive − Negative) / (Positive + Negative + 0.000001) |
| Subjectivity Score | (Positive + Negative) / (Cleaned Word Count + 0.000001) |
| Average Sentence Length | Total Words / Total Sentences |
| Percentage of Complex Words | Complex Words / Total Words |
| Fog Index | 0.4 × (Average Sentence Length + Percentage of Complex Words) |
| Average Number of Words per Sentence | Total Words / Total Sentences |
| Complex Word Count | Number of words with more than 2 syllables |
| Word Count | Number of cleaned words |
| Syllables per Word | Total Syllables / Total Words |
| Personal Pronouns | Count of I, we, my, ours, us |
| Average Word Length | Total Characters / Total Words |

Percentage of Complex Words is stored as a fraction (for example 0.35), not multiplied by 100. A small value (`0.000001`) is added to the sentiment denominators to avoid division by zero. "Words" here means the cleaned words (after stop-word and punctuation removal).

---

## Project Structure

```text
blackcoffer_project/
│
├── main.py                  # Main execution script
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation
│
├── StopWords/               # Stop-word files from the assignment
├── MasterDictionary/        # Positive and negative word lists
│
├── Input.xlsx               # Generated: article URLs
├── articles/                # Generated: 1.txt, 2.txt, ...
└── Output.xlsx              # Generated: final results
```

## Installation and Setup

**Requirements:** Python 3.8 or higher and an internet connection.

1. Unzip the project folder and open a terminal inside it.
2. Make sure the `StopWords/` and `MasterDictionary/` folders contain the assignment files.
3. Install the dependencies:

```bash
pip install -r requirements.txt
```

4. Run the project:

```bash
python main.py
```

NLTK data is downloaded automatically on the first run. A full run takes about 15–20 minutes.

## Execution Options

```bash
python main.py --skip-urls      # reuse the existing Input.xlsx
python main.py --skip-extract   # reuse the articles/ folder, only redo the analysis
```

If the script stops, run it again. Articles that are already downloaded are skipped.

## Implementation Details

**Stop words.** Some lines look like `AFGHANI | Afghanistan`. The loader splits on `|` and keeps only the word. Files are read with `latin-1` encoding because some contain non-UTF-8 characters.

**Syllables.** Groups of vowels are counted, and words ending in `es` or `ed` lose one syllable. Words with more than two syllables are complex. This is an approximate rule, not a pronunciation dictionary.

**Personal pronouns.** A regular expression finds I, we, my, ours and us. The uppercase `US` (the country) is not counted.

## Known Limitations

1. **Website changes:** if the site's HTML changes, update the class name in `extract_text()`.
2. **Failed URLs:** a few URLs may be unavailable or may be list pages, not articles. Their rows stay empty.
3. **Syllable estimate:** the vowel-group method is approximate.
4. **Readability values:** they are calculated on cleaned words, so they can differ from standard readability tools that use the full text.

## Troubleshooting

| Problem | Solution |
|---|---|
| `python` command not found | Try `py main.py` or `python3 main.py` |
| Missing NLTK resources | Check your internet connection and run again |
| Excel permission error | Close `Input.xlsx` and `Output.xlsx`, then run again |
| Empty article files | Check the page HTML and update `extract_text()` |
| Missing dictionary files | Put the assignment files in `StopWords/` and `MasterDictionary/` |

## Dependencies

| Library | Purpose |
|---|---|
| Requests | Download web pages |
| BeautifulSoup4 | Parse HTML and extract the article |
| lxml | Read sitemap XML files |
| Pandas | Handle tables and Excel data |
| OpenPyXL | Read and write Excel files |
| NLTK | Tokenization and stop words |

---

**Developed by:** Aakash Kumar
**Technology Stack:** Python | Requests | BeautifulSoup | NLTK | Pandas | Excel