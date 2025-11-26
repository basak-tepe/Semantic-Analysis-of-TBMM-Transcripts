import re
from elasticsearch import Elasticsearch
from elasticsearch import helpers
import glob 
import os

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
        r"(\d+)\.\-\s*(.*?)\s+Milletvekili\s+(.*?)’?(?:ın|in|un|ün|nın|nin|nun|nün),\s*(.*?)açıklaması\s+(\d+(?::\d+)?)",
        re.UNICODE | re.IGNORECASE | re.DOTALL
    )

    speeches = []
    for match in pattern.finditer(aciklamalar_text):
        speeches.append({
            "speech_no": match.group(1),
            "province": match.group(2).strip(),
            "speech_giver": match.group(3).strip(),
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
    es = Elasticsearch(hosts=["http://localhost:9200"])
    index_name = "parliament_speeches"
    
    actions = []

    terms_and_years = {28 : [1], 27: [1, 2, 3, 4, 5, 6], 26: [1, 2, 3], 25: [1, 2], 24: [1, 2, 3], 23:[1,2,3,4,5]}

    for term, years in terms_and_years.items():
        for year in years:
            # Adjust this to your local path
            #folder_path = f"/Volumes/PortableSSD/TPT/TXTs/d{term}-y{year}_txts/"
            folder_path = f"TXTs/d{term}-y{year}_txts/"
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
                            "speech_title": s["speech_title"],
                            "page_ref": s["page_ref"],
                            "content": speech_text if speech_text else ""
                        }
                    }
                    actions.append(doc)

    if actions:
        try:
            success, failed = helpers.bulk(es, actions, stats_only=True)
            print(f"\n✅ Indexed {success} documents, ❌ failed {failed}")
        except Exception as e:
            print("Bulk indexing failed ❌:", e)
    else:
        print("⚠️ No documents to index")