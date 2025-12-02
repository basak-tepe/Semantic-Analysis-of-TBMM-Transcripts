import re
import os
import glob
from elasticsearch import Elasticsearch, helpers
import json
from elasticsearch.helpers import BulkIndexError
import csv
import difflib
import ast
import sys

# Ensure we can import get_mp_details if running from a different directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from get_mp_details import get_mp_details
except ImportError:
    print("Warning: Could not import get_mp_details. MP enrichment will be skipped.")
    get_mp_details = None

LOOKUP_FILE = "mp_lookup.csv"
mp_lookup = {}

def load_mp_lookup():
    """Load the MP lookup table from CSV into a dictionary."""
    global mp_lookup
    if os.path.exists(LOOKUP_FILE):
        try:
            with open(LOOKUP_FILE, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse terms list safely
                    try:
                        terms = ast.literal_eval(row.get('terms', '[]'))
                    except (ValueError, SyntaxError):
                        terms = []
                    
                    mp_lookup[row['speech_giver']] = {
                        'party': row['political_party'],
                        'terms': terms
                    }
            print(f"✅ Loaded {len(mp_lookup)} entries from {LOOKUP_FILE}")
        except Exception as e:
            print(f"⚠️ Error loading lookup file: {e}")
            mp_lookup = {}
    else:
        print(f"ℹ️ No existing {LOOKUP_FILE} found. Starting fresh.")
        mp_lookup = {}

def save_mp_lookup():
    """Save the current MP lookup table to CSV."""
    try:
        with open(LOOKUP_FILE, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['speech_giver', 'political_party', 'terms'])
            writer.writeheader()
            for name, data in mp_lookup.items():
                writer.writerow({
                    'speech_giver': name,
                    'political_party': data.get('party'),
                    'terms': data.get('terms', [])
                })
        print(f"💾 Saved lookup table to {LOOKUP_FILE}")
    except Exception as e:
        print(f"❌ Error saving lookup file: {e}")

def find_mp_info(name):
    """
    Find MP info using exact match, fuzzy match, or API lookup.
    Returns dict with 'party' and 'terms'.
    """
    if not name:
        return {'party': None, 'terms': []}

    # 1. Exact Match
    if name in mp_lookup:
        return mp_lookup[name]
    
    # 2. Fuzzy Match in Cache
    # Find close matches in existing keys
    matches = difflib.get_close_matches(name, mp_lookup.keys(), n=1, cutoff=0.85)
    if matches:
        match_name = matches[0]
        # print(f"   ... Fuzzy match found: '{name}' -> '{match_name}'")
        # Return the cached data for the matched name
        # We also cache this new variation to speed up future lookups
        data = mp_lookup[match_name]
        mp_lookup[name] = data
        return data

    # 3. API Lookup
    if get_mp_details:
        # print(f"   ... API Lookup for: '{name}'")
        details = get_mp_details(name)
        if details:
            data = {
                'party': details['party'],
                'terms': details['terms']
            }
            mp_lookup[name] = data
            return data
    
    # 4. Not Found / API Failed
    # Cache empty result to avoid repeated failed lookups
    fallback = {'party': None, 'terms': []}
    mp_lookup[name] = fallback
    return fallback

FOUND_SUMMARY_BUT_NO_SPEECH = 0
FOUND_SUMMARY_TOTAL = 0
FOUND_SPEECH_TOTAL = 0

LETTER_CHARS = "A-Za-zÇĞİÖŞÜçğıöşüİıîéâûöüÂÎÛ"
POSSESSIVE_SUFFIX_RE = re.compile(
    r"['’]?\s*(?:nın|nin|nun|nün|ın|in|un|ün)$",
    re.IGNORECASE,
)


def normalize_raw_text(text):
    """
    Remove common typography artifacts (soft hyphen, NBSP, inline syllable
    breaks) so downstream regexes see contiguous words.
    """
    text = text.replace("­", "").replace("\xa0", " ")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(
        rf"([{LETTER_CHARS}])-\s*([{LETTER_CHARS}])",
        r"\1\2",
        text,
    )
    return text


def strip_possessive_suffix(text: str) -> str:
    return POSSESSIVE_SUFFIX_RE.sub("", text).strip()

def make_flexible_pattern(text):
    """
    Converts a name like 'Türkân Turgut Arıkan' into a regex pattern that matches
    both accented and unaccented variants.
    Example: Türkân -> T[UÜ]RK[ÂA]N
    """
    replacements = {
        "ç": "[cç]", "Ç": "[cÇC]",
        "ğ": "[gğ]", "Ğ": "[gĞG]",
        "ı": "[ıiItT]", "İ": "[İIitT]",
        "ö": "[oöOÖ]", "Ö": "[oöOÖ]",
        "ş": "[sşSŞ]", "Ş": "[sşSŞ]",
        "ü": "[uüUÜ]", "Ü": "[uüUÜ]",
        "â": "[aâAÂ]", "Â": "[aâAÂ]",
        "î": "[iîIÎtT]", "Î": "[iîIÎtT]",
        "û": "[uûUÛ]", "Û": "[uûUÛ]",
        "i": "[ıiItTÎî]", "İ": "[İIitTÎî]", #sometimes i is written as Î 
        "I": "[iİıIîÎ]",
    }
    pattern = ""
    for ch in text:
        pattern += replacements.get(ch, re.escape(ch))
    return pattern

def extract_session_id(folder_name, term, year):
    match = re.search(r"(\d{3})$", folder_name)
    if not match:
        return None
    session_suffix = match.group(1)      # "001" for tbmm17001001
    return f"term{term}-year{year}-session{session_suffix}"

def extract_speech_summaries(raw_text):
    global FOUND_SUMMARY_TOTAL
    
    raw_text = normalize_raw_text(raw_text)
    summaries = []

    # 1) Extract ONLY the A) GÜNDEM DIŞI KONUŞMALAR block
    index_match = re.search(
        r"A\)\s*GÜNDEM\s*DIŞI\s*KONUŞMALAR[^\n]*\n(.*?)(?=\n\s*(?:[B-Z]\)|[IVXL]+\.)|\Z)",
        raw_text,
        re.S | re.IGNORECASE
    )

    if not index_match:
        print("No GÜNDEM DIŞI KONUŞMALAR section found.")
        return summaries

    index_block = index_match.group(1)

    # 2) Main item extraction pattern
    pattern = re.compile(
        r"""
        (\d+)\.\s*[—-]\s*                              # 1. —
        ([A-Za-zÇĞİÖŞÜçğıöşüİıîéâûöü\s-]+?)\s+         # Province
        (?:Milletvekili|Bakanı(?:\s+[A-Za-zÇĞİÖŞÜçğıöşüİıîéâûöü\s-]+?)*)\s+  
        ([A-Za-zÇĞİÖŞÜçğıöşüİıîéâûöü.\s-]+)\s*
        (?:['’]?(?:nın|nin|nun|nün|ın|in|un|ün))?,?\s*  
        ([\s\S]*?)(?:konuşması|cevabı|(?=\d+\.\s*[—-])) 
        """,
        re.IGNORECASE | re.VERBOSE
    )

    matches = list(pattern.finditer(index_block))

    # 3) Numbering check — enforce (n+1)
    expected_no = 1

    for m in matches:
        current_no = int(m.group(1))

        if current_no != expected_no:
            print(f"STOP: found item {current_no} but expected {expected_no}. Ending extraction.")
            break

        summaries.append({
            "speech_no": m.group(1).strip(),
            "province": strip_possessive_suffix(re.sub(r"\s+", " ", m.group(2).strip())),
            "speech_giver": strip_possessive_suffix(re.sub(r"\s+", " ", m.group(3).strip())),
            "speech_title": re.sub(r"\s+", " ", m.group(4).strip())
        })

        expected_no += 1

    FOUND_SUMMARY_TOTAL += len(summaries)
    return summaries




def get_name_prefix(name: str, length: int = 2) -> str:
    if len(name) < length:
        return name
    return name[:length]


def extract_full_speech(raw_text, speech_no, speaker_name):
    """
    Extracts the full actual speech (including the header line with the speaker name),
    after the second occurrence of 'GÜNDEM DIŞI KONUŞMALAR'.
    
    Stops when the next speech (n+1. —) begins or when 'BAŞKAN' starts speaking.
    Diacritic-tolerant.
    """

    # 1️⃣ Locate the second 'GÜNDEM DIŞI KONUŞMALAR'
    global FOUND_SUMMARY_BUT_NO_SPEECH
    raw_text = normalize_raw_text(raw_text)
    matches = list(re.finditer(r"GÜNDEM\s+DIŞI\s+KONUŞMALAR", raw_text, re.I))
    if len(matches) < 2:
        return None
    transcript_part = raw_text[matches[1].end():]

    # 2️⃣ Build flexible regex for the first letters of the speaker name
    name_prefix = get_name_prefix(speaker_name, length=2)
    flexible_name = make_flexible_pattern(name_prefix)
    # print(f"Flexible prefix for '{speaker_name}' -> '{name_prefix}': {flexible_name}") 
    
    # 3️⃣ Locate the speech start (include the name line)
    start_match = re.search(
        rf"{flexible_name}[A-ZÇĞİÖŞÜÂÎÛ'\s.-]*\s*\(.*?\)\s*[—-]", 
        transcript_part, 
        re.S | re.I
    )
    if not start_match:
        FOUND_SUMMARY_BUT_NO_SPEECH += 1
        print(f"Could not find start of speech for {speaker_name} (speech no {speech_no})")
        return None

    start_index = start_match.start()

    # 4️⃣ Locate the end (next numbered speech or BAŞKAN)
    next_num = int(speech_no) + 1
    end_match = re.search(
        rf"(?={next_num}\.\s*[—-]|BAŞKAN\s*[—-])", 
        transcript_part[start_index:], 
        re.S | re.I
    )
    end_index = start_index + end_match.start() if end_match else len(transcript_part)

    # 5️⃣ Extract and normalize
    full_speech = transcript_part[start_index:end_index]
    full_speech = re.sub(r"\s+", " ", full_speech).strip()

    return full_speech

def extract_full_speeches(raw_text, summaries):
    """
    For each speech summary, extract the full speech text.
    Returns a list of dicts with speech_no, province, speech_giver, speech_title, and content.
    """
    full_speeches = []

    for summary in summaries:
        speech_no = summary["speech_no"]
        province = summary["province"]
        speech_giver = summary["speech_giver"]
        speech_title = summary["speech_title"]

        content = extract_full_speech(raw_text, speech_no, speech_giver)
        if content:
            full_speeches.append({
                "speech_no": speech_no,
                "province": province,
                "speech_giver": speech_giver,
                "speech_title": speech_title,
                "content": content
            })

    return full_speeches


if __name__ == "__main__":
    # Load existing MP info
    load_mp_lookup()

    es = Elasticsearch(hosts=["http://localhost:9200"])
    index_name = "parliament_speeches"

    actions = []

    terms_and_years = {
        17: [1,2,3,4,5],
        18: [1,2,3,4,5,6],
        19: [1,2,3,4,5],
        20: [1,2,3,4],
        21: [1,2,3,4,5],
        22: [1,2,3,4,5],
    }

    try:
        for term, years in terms_and_years.items():
          for year in years:
            folder_path = f"TXTs_deepseek/d{term}-y{year}_TXTs/"
            
            # Check if directory exists
            if not os.path.exists(folder_path):
                print(f"⚠️ Directory not found: {folder_path}")
                continue

            # find all result.mmd files inside subfolders
            mmd_files = glob.glob(os.path.join(folder_path, "*", "result.mmd"))

            for filepath in mmd_files:
                filename = os.path.basename(filepath)
                parent_folder = os.path.basename(os.path.dirname(filepath))  # e.g. tbmm17001001

                # extract session ID from the folder name now
                session_id = extract_session_id(parent_folder, term, year)

                print(f"\n📂 Processing {parent_folder}/result.mmd")

                with open(filepath, "r", encoding="utf-8") as f:
                    raw_text = normalize_raw_text(f.read())

                summaries = extract_speech_summaries(raw_text)
                print(f"Found {len(summaries)} speech summaries.")

                full_speeches = extract_full_speeches(raw_text, summaries)
                print(f"Found {len(full_speeches)} speeches.")

                FOUND_SPEECH_TOTAL += len(full_speeches)

                for s in full_speeches:
                    # Enrich with MP Info
                    mp_info = find_mp_info(s["speech_giver"])

                    doc = {
                        "_index": index_name,
                        "_id": f"{session_id}-{s['speech_no']}",
                        "_source": {
                            "session_id": session_id,
                            "term": term,
                            "year": year,
                            "file": filename,
                            "speech_no": int(s["speech_no"]),
                            "province": s["province"],
                            "speech_giver": s["speech_giver"],
                            "political_party": mp_info.get('party'),
                            "terms_served": mp_info.get('terms'),
                            "speech_title": s["speech_title"],
                            "page_ref": s.get("page_ref"),
                            "content": s["content"],
                        },
                    }
                    actions.append(doc)

        if actions:
            try:
                helpers.bulk(es, actions, raise_on_error=True)
                print(f"\n✅ Indexed {len(actions)} documents successfully.")
                
            except BulkIndexError as e:
                with open("failed_docs.json", "w") as f:
                    json.dump(e.errors, f, indent=2)
                print(f"❌ {len(e.errors)} docs failed — saved to failed_docs.json")
            
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user.")
    finally:
        # Always save lookup table at the end
        save_mp_lookup()
        
        # Print stats
        # success, failed = helpers.bulk(es, actions, stats_only=True)
        # print(f"\n✅ Indexed {success} documents, ❌ failed {failed}")
        print(f"Total speeches processed: {FOUND_SPEECH_TOTAL}")
        print(f"Total summaries found: {FOUND_SUMMARY_TOTAL}")
        print(f"Summaries without speeches: {FOUND_SUMMARY_BUT_NO_SPEECH}")
