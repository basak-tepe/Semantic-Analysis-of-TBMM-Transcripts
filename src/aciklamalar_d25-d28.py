import re
from elasticsearch import Elasticsearch
from elasticsearch import helpers
import glob 
import os
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

# Import MP name normalization functions
try:
    from mp_name_normalizer import normalize_mp_name, is_valid_name_length, find_similar_names
except ImportError:
    print("Warning: Could not import mp_name_normalizer. Name normalization will be skipped.")
    normalize_mp_name = None
    is_valid_name_length = None
    find_similar_names = None

LOOKUP_FILE = "mp_lookup.csv"
mp_lookup = {}

DATE_LOOKUP_FILE = "session_dates_lookup.csv"
date_lookup = {}

def load_date_lookup():
    """Load the session date lookup table from CSV into a dictionary."""
    global date_lookup
    lookup_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DATE_LOOKUP_FILE)
    
    if os.path.exists(lookup_path):
        try:
            with open(lookup_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_lookup[row['filename']] = row['session_date']
            print(f"✅ Loaded {len(date_lookup)} session dates from {DATE_LOOKUP_FILE}")
        except Exception as e:
            print(f"⚠️ Error loading date lookup file: {e}")
            date_lookup = {}
    else:
        print(f"ℹ️ No {DATE_LOOKUP_FILE} found. Session dates will be null.")
        date_lookup = {}

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

def extract_session_id(filename,term,year):
    """
    Extract session ID from the last two digits in the filename.
    EVERY SPEECH SHOULD HAVE A UNIQUE ID BASED ON SESSION_ID + SPEECH NO. 
    SPEECH NO IS PROVIDED LATER IN THE INDEX ID FIELD.
    Ex:
      tbmm28002002.txt -> 'd28-y1-s2' #this is just session id, not unique for each speech
      tbmm19017005.txt -> 'd19-y1-s5'


    """
    match = re.search(r"(\d{3})\.txt$", filename) # captures last three digits before .txt
    if not match:
        return None
    session_num = int(match.group(1))  # drops leading zero
    return f"term{term}-year{year}-session{session_num}"

def extract_aciklamalar(text):
    """
    Grab the AÇIKLAMALAR section, regardless of Roman numeral prefix.
    """
    match = re.search(r"[IVXLCDM]+\.\-\s*AÇIKLAMALAR(.*?)(?:[IVXLCDM]+\.\-|$)", 
                      text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""

def extract_speech_summaries(aciklamalar_text):
    """Parse the list of speech summaries from the AÇIKLAMALAR section (multiline safe)."""
    pattern = re.compile(
        r"(\d+)\.\-\s*(.*?)\s+Milletvekili\s+(.*?)’?(?:ın|in|un|ün|nın|nin),\s*(.*?)açıklaması\s+(\d+(?::\d+)?)",
        re.UNICODE | re.IGNORECASE | re.DOTALL
    )

    speeches = []
    for match in pattern.finditer(aciklamalar_text):
        # Extract and normalize the speech giver name
        raw_name = match.group(3).strip()
        
        # Apply name normalization if available
        if normalize_mp_name:
            normalized_name = normalize_mp_name(raw_name)
            
            # Handle long names (likely extraction errors)
            if is_valid_name_length and not is_valid_name_length(normalized_name, max_length=70):
                # Try to find matching shorter name from lookup
                if find_similar_names and mp_lookup:
                    matching_names = find_similar_names(
                        normalized_name, 
                        list(mp_lookup.keys()), 
                        threshold=0.9,
                        lookup_data=mp_lookup
                    )
                    if matching_names:
                        normalized_name = matching_names[0]  # Use first match
                        print(f"   ⚠️  Mapped long name to: {normalized_name}")
                    else:
                        print(f"   ⚠️  Could not resolve long name: {normalized_name[:50]}...")
        else:
            normalized_name = raw_name
        
        speeches.append({
            "speech_no": match.group(1),
            "province": match.group(2).strip(),
            "speech_giver": normalized_name,
            "speech_title": re.sub(r"\s+", " ", match.group(4)).strip(),  # normalize whitespace
            "page_ref": match.group(5)
        })
    return speeches

def extract_full_speech(text, speech_no, province, speaker):
    """
    Find the full speech: locate the *second occurrence* of the summary
    and grab everything until the next summary or next section.
    """
    start_pattern = re.compile(
        rf"{speech_no}\.\-\s*{province}\s+Milletvekili\s+{re.escape(speaker)}.*?açıklaması",
        re.UNICODE | re.DOTALL
    )

    matches = list(start_pattern.finditer(text))
    if len(matches) < 2:
        return None  # didn't find the repeated occurrence

    # Take the second occurrence (real speech)
    start_match = matches[1]
    start_idx = start_match.end()

    # End marker: next speech or next Roman numeral section
    end_pattern = re.compile(
        r"(?:^\s*\d+\.\-\s*.*?Milletvekili|^[IVXLCDM]+\.\-)",
        re.MULTILINE | re.UNICODE
    )

    end_match = end_pattern.search(text, start_idx)
    end_idx = end_match.start() if end_match else len(text)

    speech_block = text[start_idx:end_idx].strip()
    return speech_block if speech_block else None

# ---------------- MAIN ---------------- #

if __name__ == "__main__":
    # Load existing MP info
    load_mp_lookup()
    load_date_lookup()

    es = Elasticsearch(hosts=["http://localhost:9200"])
    index_name = "parliament_speeches"
    
    actions = []

    terms_and_years = {28 : [1], 27: [1, 2, 3, 4, 5, 6], 26: [1, 2, 3], 25: [1, 2], 24: [1, 2, 3], 23:[1,2,3,4,5]}

    try:
        for term, years in terms_and_years.items():
            for year in years:
                # Adjust this to your local path
                folder_path = f"TXTs/d{term}-y{year}_txts/"
                # Check if directory exists to avoid glob errors or empty loops on missing drives
                if not os.path.exists(folder_path):
                    print(f"⚠️ Directory not found: {folder_path}")
                    continue

                for filepath in glob.glob(os.path.join(folder_path, "*.txt")):
                    if filepath.endswith(("fih.txt", "gnd.txt")):
                        continue

                    filename = os.path.basename(filepath)
                    session_id = extract_session_id(filename,term,year)
                    print(f"\n📂 Processing {filename}")

                    with open(filepath, "r", encoding="utf-8") as f:
                        raw_text = f.read()

                    aciklamalar = extract_aciklamalar(raw_text)
                    summaries = extract_speech_summaries(aciklamalar)
                    print(f"Found {len(summaries)} speech summaries.")

                    for s in summaries:
                        speech_text = extract_full_speech(raw_text, s["speech_no"], s["province"], s["speech_giver"])
                        s["content_preview"] = speech_text[:100] + "..." if speech_text else None
                        s["content_length"] = len(speech_text) if speech_text else 0

                        # Enrich with MP Info
                        mp_info = find_mp_info(s["speech_giver"])
                        
                        # Look up session date
                        session_date = date_lookup.get(filename)

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
                                "page_ref": s["page_ref"],
                                "content": speech_text if speech_text else "",
                                "session_date": session_date
                            }
                        }
                        actions.append(doc)
        
        if actions:
            success, failed = helpers.bulk(es, actions, stats_only=True)
            print(f"\n✅ Indexed {success} documents, ❌ failed {failed}")
        else:
            print("⚠️ No documents to index")

    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user.")
    finally:
        # Always save lookup table at the end
        save_mp_lookup()
