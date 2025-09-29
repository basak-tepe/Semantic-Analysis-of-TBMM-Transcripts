from elasticsearch import Elasticsearch 

es = Elasticsearch(hosts=["http://localhost:9200"])
index_name = "parliament_speeches"

res = es.search(
    index=index_name,
    query={
        "match": {"content": "demokrasi"}  # example word in Turkish
    },
    size=3
)
for hit in res["hits"]["hits"]:
    print(f"{hit['_source']['speech_giver']}: {hit['_source']['speech_title']}")