#!/usr/bin/env python3
import csv
import json
import os
from collections import defaultdict

# Increase field size limit
csv.field_size_limit(10000000)

# Read CSV file
csv_path = os.path.join(os.path.dirname(__file__), '../../data/topic_summary.csv')
json_path = os.path.join(os.path.dirname(__file__), '../src/data/topicData.json')

data = []
mp_total_speeches = defaultdict(int)

# First pass: collect data and calculate total speeches per MP
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            speech_giver = row.get('speech_giver', '')
            topic = int(row['topic']) if row['topic'] else -1
            count = int(row['count']) if row['count'] else 0
            
            # Sum up all speeches for this MP
            mp_total_speeches[speech_giver] += count
            
            # Only keep essential data, skip large text fields
            topic_name = row.get('Name', f'Topic {topic}')
            # Truncate topic name if too long
            if len(topic_name) > 100:
                topic_name = topic_name[:100] + '...'
            
            data.append({
                'speech_giver': speech_giver,
                'topic': topic,
                'count': count,
                'topicName': topic_name,
            })
        except (ValueError, KeyError) as e:
            continue

# Second pass: add totalCount to each entry
for entry in data:
    entry['totalCount'] = mp_total_speeches[entry['speech_giver']]

# Write JSON file
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Converted {len(data)} topic-MP relationships to JSON")
print(f"Unique MPs: {len(set(d['speech_giver'] for d in data))}")
print(f"Unique Topics: {len(set(d['topic'] for d in data))}")
print(f"Sample MP totals: {dict(list(mp_total_speeches.items())[:5])}")

