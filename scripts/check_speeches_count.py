#!/usr/bin/env python3
"""
Check the number of speeches with keywords but without topic labels.
"""
import os
from elasticsearch import Elasticsearch

# Get ES host from environment or use default
es_host = os.getenv('ELASTICSEARCH_HOST', 'http://localhost:9200')
es_index = os.getenv('ELASTICSEARCH_INDEX', 'parliament_speeches')

print(f'🔌 Connecting to Elasticsearch at {es_host}...')
es = Elasticsearch(hosts=[es_host])

if not es.ping():
    print('❌ Failed to connect to Elasticsearch')
    exit(1)

print('✅ Connected to Elasticsearch\n')

# Count speeches with keywords but without topic_id
query_no_topic_id = {
    'query': {
        'bool': {
            'must': [
                {'exists': {'field': 'keywords'}},
                {'exists': {'field': 'keywords_embedding'}}
            ],
            'must_not': [
                {'exists': {'field': 'keywords'}}
            ]
        }
    }
}

# Count speeches with keywords but without topic_label
query_no_topic_label = {
    'query': {
        'bool': {
            'must': [
                {'exists': {'field': 'keywords'}},
                {'exists': {'field': 'keywords_embedding'}}
            ],
            'must_not': [
                {'exists': {'field': 'hdbscan_topic_label'}}
            ]
        }
    }
}

# Count speeches with keywords but without either topic field
query_no_topic = {
    'query': {
        'bool': {
            'must': [
                {'exists': {'field': 'keywords'}},
                {'exists': {'field': 'keywords_embedding'}}
            ],
            'must_not': [
                {'exists': {'field': 'hdbscan_topic_id'}},
                {'exists': {'field': 'hdbscan_topic_label'}}
            ]
        }
    }
}

# Count total speeches with keywords and embeddings
query_total = {
    'query': {
        'bool': {
            'must': [
                {'exists': {'field': 'keywords'}},
                {'exists': {'field': 'keywords_embedding'}}
            ]
        }
    }
}

print('📊 Counting speeches...\n')

count_no_topic_id = es.count(index=es_index, body=query_no_topic_id)['count']
count_no_topic_label = es.count(index=es_index, body=query_no_topic_label)['count']
count_no_topic = es.count(index=es_index, body=query_no_topic)['count']
count_total = es.count(index=es_index, body=query_total)['count']

print('=' * 60)
print('📊 Statistics:')
print('=' * 60)
print(f'   Total speeches with keywords + embeddings: {count_total:,}')
print(f'   Speeches WITHOUT hdbscan_topic_id: {count_no_topic_id:,}')
print(f'   Speeches WITHOUT hdbscan_topic_label: {count_no_topic_label:,}')
print(f'   Speeches WITHOUT both topic fields: {count_no_topic:,}')
print(f'   Speeches WITH topics: {count_total - count_no_topic:,}')
print('=' * 60)

