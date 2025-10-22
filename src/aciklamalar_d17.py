import re
import os
import glob
from elasticsearch import Elasticsearch, helpers
import json
from elasticsearch.helpers import BulkIndexError

FOUND_SUMMARY_BUT_NO_SPEECH = 0
FOUND_SUMMARY_TOTAL = 0
FOUND_SPEECH_TOTAL = 0

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
    }
    pattern = ""
    for ch in text:
        pattern += replacements.get(ch, re.escape(ch))
    return pattern

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


def extract_speech_summaries(raw_text):
    global FOUND_SUMMARY_TOTAL
    raw_text = raw_text.replace("­", "").replace("\xa0", " ")  # remove soft hyphens 
    raw_text = re.sub(r"(\w)-\n(\w)", r"\1\2", raw_text)  # merge line breaks
    

    summaries = []

    # extract section
    index_match = re.search(
        r"A\)\s*GÜNDEM\s*DIŞI\s*KONUŞMALAR[^\n]*\n(.*?)(?=\n\s*(?:[B-Z]\)|[IVXL]+\.)|\Z)",
        raw_text, re.S | re.IGNORECASE
    )
    if not index_match:
        print("No GÜNDEM DIŞI KONUŞMALAR section found.")
        return summaries

    index_block = index_match.group(1) 
    #print(f"index_block {index_block}")

    pattern = re.compile(
    r"""
    (\d+)\.\s*[—-]\s*                              # e.g. 1. —
    ([A-Za-zÇĞİÖŞÜçğıöşüİıîéâûöü\s]+?)\s+          # Province (allow accents)
    (?:Milletvekili|Bakanı(?:\s+[A-Za-zÇĞİÖŞÜçğıöşüİıîéâûöü\s]+?)*)\s+  # MP or Minister (multi-word)
    ([A-Za-zÇĞİÖŞÜçğıöşüİıîéâûöü\s]+?)'?           # Speaker name
    \s*(?:nın|nin|nun|nün|ın|in|un|ün),?\s*                    # possessive
    ([\s\S]*?)(?:konuşması|cevabı|(?=\d+\.\s*[—-])) # topic until keyword or next item
    """,
    re.IGNORECASE | re.VERBOSE
)

    for m in pattern.finditer(index_block):
        #print("Matched summary:", m.groups())
        summaries.append({
            "speech_no": m.group(1).strip(),
            "province": re.sub(r"\s+", " ", m.group(2).strip()),
            "speech_giver": re.sub(r"\s+", " ", m.group(3).strip()),
            "speech_title": re.sub(r"\s+", " ", m.group(4).strip())
        })
    FOUND_SUMMARY_TOTAL += len(summaries)
    return summaries




def extract_full_speech(raw_text, speech_no, speaker_name):
    """
    Extracts the full actual speech (including the header line with the speaker name),
    after the second occurrence of 'GÜNDEM DIŞI KONUŞMALAR'.
    
    Stops when the next speech (n+1. —) begins or when 'BAŞKAN' starts speaking.
    Diacritic-tolerant.
    """

    # 1️⃣ Locate the second 'GÜNDEM DIŞI KONUŞMALAR'
    global FOUND_SUMMARY_BUT_NO_SPEECH
    raw_text = raw_text.replace("­", "").replace("\xa0", " ")
    matches = list(re.finditer(r"GÜNDEM\s+DIŞI\s+KONUŞMALAR", raw_text, re.I))
    if len(matches) < 2:
        return None
    transcript_part = raw_text[matches[1].end():]

    # 2️⃣ Build flexible regex for the speaker name
    flexible_name = make_flexible_pattern(speaker_name)
    #print(f"Flexible pattern for '{speaker_name}': {flexible_name}") 
    
    # 3️⃣ Locate the speech start (include the name line)
    start_match = re.search(
        rf"{flexible_name}\s*\(.*?\)\s*[—-]", 
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
    es = Elasticsearch(hosts=["http://localhost:9200"])
    index_name = "parliament_speeches_d17"

    actions = []

    terms_and_years = {
        17: [1,2,3,4,5],
        18: [1,2,3,4,5,6],
        19: [1,2,3,4,5],
        20: [1,2,3,4],
        21: [1,2,3,4,5],
        22: [1,2,3,4,5],
    }

    for term, years in terms_and_years.items():
        for year in years:
            folder_path = f"TXTs/d{term}-y{year}_txts/"
            for filepath in glob.glob(os.path.join(folder_path, "*.txt")):
                if filepath.endswith(("fih.txt", "gnd.txt")):
                    continue

                filename = os.path.basename(filepath)
                session_id = extract_session_id(filename, term, year)
                print(f"\n📂 Processing {filename}")

                with open(filepath, "r", encoding="utf-8") as f:
                    raw_text = f.read()

                summaries = extract_speech_summaries(raw_text)
                print(f"Found {len(summaries)} speech summaries.")
                full_speeches = extract_full_speeches(raw_text, summaries)
                print(f"Found {len(full_speeches)} speeches.")
                FOUND_SPEECH_TOTAL += len(full_speeches)

                for s in full_speeches:
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
        
        #success, failed = helpers.bulk(es, actions, stats_only=True)
    
        #print(f"\n✅ Indexed {success} documents, ❌ failed {failed}")
        finally:
            print(f"Total speeches processed: {FOUND_SPEECH_TOTAL}")
            print(f"Total summaries found: {FOUND_SUMMARY_TOTAL}")
            print(f"Summaries without speeches: {FOUND_SUMMARY_BUT_NO_SPEECH}")
    else:
        print("⚠️ No documents to index")

