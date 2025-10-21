import re
import os
import glob
from elasticsearch import Elasticsearch, helpers

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
    """
    Extracts 'Gündem Dışı Konuşmalar' section from the index.
    Returns a list of dicts with speech_no, province, speech_giver, and speech_title.
    """
    summaries = []

    # Locate the index section that lists the speeches
    index_match = re.search(
        r"A\)\s*GÜNDEM DIŞI KONUŞMALAR(.*?)(?:B\)|$)",
        raw_text,
        re.S | re.IGNORECASE
    )
    if not index_match:
        return summaries

    index_block = index_match.group(1)

    # Match numbered lines like:
    # 1. — İstanbul Milletvekili Günseli Özkaya'nın, Hükümetin faiz politikasıyla ilgili gündem dışı konuşması.
    pattern = re.compile(
    r"(\d+)\.\s*[—-]\s*(.*?)\s+Milletvekili\s+(.*?)'(?:nın|nin|nun|nün),?\s*(.*?)\.\s*\n?",
    re.IGNORECASE | re.DOTALL
)

    for m in pattern.finditer(index_block):
        summaries.append({
            "speech_no": m.group(1).strip(),
            "province": m.group(2).strip(),
            "speech_giver": m.group(3).strip(),
            "speech_title": m.group(4).replace("\n", " ").strip(),
        })

    return summaries


def extract_full_speeches(raw_text, summaries):
    """
    For each summary entry, extracts the corresponding full speech content.
    Returns the same list with 'content' and 'page_ref' added.
    """
    results = []
    for i, s in enumerate(summaries):
        # Match the beginning of this specific speech in the main text
        start_pattern = rf"{s['speech_no']}\.\s*[—-]\s*{re.escape(s['province'])}\s+Milletvekili\s+{re.escape(s['speech_giver'])}"
        start_match = re.search(start_pattern, raw_text, re.IGNORECASE)

        if not start_match:

            continue

        start_pos = start_match.start()

        # Find where the next speech starts (or end of file)
        if i + 1 < len(summaries):
            next_speech_no = summaries[i + 1]["speech_no"]
            end_pattern = rf"\n{next_speech_no}\.\s*[—-]"
            end_match = re.search(end_pattern, raw_text[start_pos:], re.IGNORECASE)
            end_pos = start_pos + end_match.start() if end_match else len(raw_text)
        else:
            end_pos = len(raw_text)

        content = raw_text[start_pos:end_pos].strip()
        results.append({**s, "content": content, "page_ref": None})

    return results


if __name__ == "__main__":
    es = Elasticsearch(hosts=["http://localhost:9200"])
    index_name = "parliament_speeches_d17"

    actions = []

    terms_and_years = {
        17: [1,2,3,4,5],
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
                full_speeches = extract_full_speeches(raw_text, summaries)
                print(f"Found {len(full_speeches)} speeches.")

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
        success, failed = helpers.bulk(es, actions, stats_only=True)
        print(f"\n✅ Indexed {success} documents, ❌ failed {failed}")
    else:
        print("⚠️ No documents to index")

