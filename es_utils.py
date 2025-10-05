from elasticsearch import Elasticsearch, helpers
from typing import List, Dict, Any, Optional

# Initialize Elasticsearch client
def get_es_client(host: str = "http://localhost:9200") -> Elasticsearch:
    """Connect to Elasticsearch."""
    es = Elasticsearch(hosts=[host])
    try:
        info = es.info()
        print("✅ Connected to Elasticsearch:", info.get("cluster_name", "unknown"))
    except Exception as e:
        print("connection failed:", e)
    return es


def create_es_index(es: Elasticsearch, index_name: str, mappings: Optional[Dict[str, Any]] = None) -> None:
    """Create an Elasticsearch index if it doesn’t exist."""
    if es.indices.exists(index=index_name):
        print(f"ℹ️ Index '{index_name}' already exists.")
        return

    default_mappings = {
        "properties": {
            "session_id": {"type": "keyword"},
            "term": {"type": "integer"},
            "year": {"type": "integer"},
            "file": {"type": "keyword"},
            "speech_no": {"type": "integer"},
            "province": {"type": "keyword"},
            "speech_giver": {"type": "text"},
            "speech_title": {"type": "text"},
            "page_ref": {"type": "keyword"},
            "content": {"type": "text"}
        }
    }
                    

    es.indices.create(index=index_name, mappings=mappings or default_mappings)
    print(f"Created index '{index_name}'.")


def delete_es_index(es: Elasticsearch, index_name: str) -> None:
    """Delete an Elasticsearch index."""
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
        print(f"🗑️ Deleted index '{index_name}'.")
    else:
        print(f"⚠️ Index '{index_name}' not found.")


def bulk_insert_documents(es: Elasticsearch, index_name: str, docs: List[Dict[str, Any]]) -> None:
    """Bulk insert multiple documents into an index."""
    if not docs:
        print("⚠️ No documents provided for bulk insert.")
        return

    actions = [
        {
            "_index": index_name,
            "_id": doc.get("_id"),
            "_source": doc["_source"] if "_source" in doc else doc
        }
        for doc in docs
    ]

    try:
        helpers.bulk(es, actions)
        print(f"Inserted {len(actions)} documents into '{index_name}'.")
    except Exception as e:
        print("Bulk insert failed:", e)








if __name__ == "__main__":
    # Example usage
    es = get_es_client()
    index_name = "parliament_speeches"

    # Delete and recreate index for demo
    delete_es_index(es, index_name)
    create_es_index(es, index_name)

