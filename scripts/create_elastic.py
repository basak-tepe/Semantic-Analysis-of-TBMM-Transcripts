from elasticsearch import Elasticsearch, helpers

# Connect to local ES instance
es = Elasticsearch(hosts=["http://localhost:9200"])

try:
    info = es.info()
    print("Connected to Elasticsearch ✅")
    print(info)
except Exception as e:
    print("Connection failed ❌:", e)

index_name = "parliament_speeches"

es.indices.delete(index=index_name, ignore=[400, 404]) # delete if exists, can be commented out after first run

# Create index with mapping if it doesn't exist
if not es.indices.exists(index=index_name):
    es.indices.create(
        index=index_name,
        mappings={
                "properties": {
                    "session_id": {"type": "keyword"},
                    "term": {"type": "integer"},
                    "year": {"type": "integer"},
                    "speech_no": {"type": "integer"},
                    "province": {"type": "keyword"},
                    "speech_giver": {"type": "text"},
                    "political_party": {"type": "keyword"},
                    "terms_served": {"type": "integer"},
                    "speech_title": {"type": "text"},
                    "page_ref": {"type": "keyword"},
                    "content": {"type": "text"},
                    "file": {"type": "keyword"},
                    "session_date": {"type": "date", "format": "dd.MM.yyyy||strict_date_optional_time||epoch_millis"},
                    "topic_id": {"type": "integer"},
                    "topic_label": {"type": "keyword"},
                    "topic_analyzed": {"type": "boolean"}
            }
        }
    )


#todo : bulk insert the docs
    




