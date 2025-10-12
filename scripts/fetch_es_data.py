# fetch_data.py
import re
import pandas as pd
from elasticsearch import Elasticsearch
from tqdm import tqdm
#from trnlp import TrnlpWord  # Optional, for Turkish tokenization
import unicodedata
import re
import nltk
from nltk.corpus import stopwords

nltk.download("stopwords") #stopwords are for filtering out common words like "and", "the", etc. because they don't add much meaning to the text

TURKISH_STOPWORDS = set(stopwords.words("turkish")) | { #adding my additional stopwords
    "bir", "sayın", "başkan", "ve", "ile", "de", "da",
    "der", "derler", "derleri", "dahi", "ancak", "fakat",
    "şu", "bu", "o", "ki", "gibi", "olan","bunun"
}

INDEX_NAME = "parliament_speeches"
ES_URL = "http://localhost:9200"
OUTPUT_FILE = "speeches_clean.csv"


def connect_elasticsearch():
    es = Elasticsearch(ES_URL)
    if not es.ping():
        raise ConnectionError("Cannot connect to Elasticsearch server.")
    print("✅ Connected to Elasticsearch.")
    return es

def fetch_all_speeches(es, index_name=INDEX_NAME):
    print(f"📥 Fetching documents from index: {index_name}")
    results = []
    page_size = 1000
    resp = es.search(index=index_name, query={"match_all": {}}, scroll="5m", size=page_size)
    scroll_id = resp["_scroll_id"]
    hits = resp["hits"]["hits"]

    while len(hits) > 0:
        for h in hits:
            results.append(h["_source"])
        resp = es.scroll(scroll_id=scroll_id, scroll="5m")
        scroll_id = resp["_scroll_id"]
        hits = resp["hits"]["hits"]

    print(f"✅ Retrieved {len(results)} documents.")
    return results

def clean_text(text: str) -> str:
    if not text:
        return ""

    # Normalize composed characters (e.g. i̇ → i)
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()

    # Remove URLs and non-letter characters (keep Turkish letters)
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"[^a-zçğıöşü\s]", " ", text)

    # Clean extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    tokens = [word for word in text.split() if word not in TURKISH_STOPWORDS and len(word) > 2]

    return " ".join(tokens)
    


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df["clean_content"] = df["content"].apply(clean_text)
    df.dropna(subset=["speech_giver", "clean_content"], inplace=True)
    print(f"✅ Cleaned {len(df)} speeches.")
    return df

if __name__ == "__main__":
    es = connect_elasticsearch()
    data = fetch_all_speeches(es)
    df = pd.DataFrame(data)
    df = preprocess(df)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"💾 Saved cleaned data to {OUTPUT_FILE}")
