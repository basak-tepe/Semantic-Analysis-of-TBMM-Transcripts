# NER Entities Frontend Integration Guide

This guide explains how to use Named Entity Recognition (NER) entities in your frontend application.

## Overview

NER entities are automatically extracted from parliamentary speeches and include:
- **PER** (Person): Names of people mentioned
- **LOC** (Location): Place names (cities, regions, etc.)
- **ORG** (Organization): Organization names (parties, institutions, etc.)

Each entity includes:
- `entity`: The entity name
- `entity_group`: Type (PER, LOC, ORG)
- `frequency`: How many times it appears in the speech
- `confidence`: Model confidence score (0.0 to 1.0)
- `wikipedia_url`: Optional Wikipedia link (if available)

## API Endpoints

### 1. Get NER Entities from Speech Search

NER entities are automatically included in speech search results:

```javascript
// Search speeches - NER entities are included in response
const response = await fetch('/api/speeches/search?q=sağlık&size=10');
const data = await response.json();

// Access NER entities from each speech
data.speeches.forEach(speech => {
  if (speech.ner_entities && speech.ner_entities.length > 0) {
    console.log(`Speech by ${speech.speech_giver} mentions:`);
    speech.ner_entities.forEach(entity => {
      console.log(`  - ${entity.entity} (${entity.entity_group})`);
    });
  }
});
```

### 2. Get Single Speech with NER Entities

```javascript
const speechId = 'term27-year5-session18-17';
const response = await fetch(`/api/speeches/${speechId}`);
const speech = await response.json();

// Display entities grouped by type
const entitiesByType = {
  PER: speech.ner_entities?.filter(e => e.entity_group === 'PER') || [],
  LOC: speech.ner_entities?.filter(e => e.entity_group === 'LOC') || [],
  ORG: speech.ner_entities?.filter(e => e.entity_group === 'ORG') || []
};
```

### 3. Search Speeches by Entity

Find all speeches that mention a specific entity:

```javascript
// Find speeches mentioning "Ankara"
const response = await fetch('/api/speeches/entities/search?entity=Ankara&size=20');
const data = await response.json();

// Find speeches mentioning a person named "Ahmet"
const personResponse = await fetch('/api/speeches/entities/search?entity=Ahmet&entity_type=PER');

// Find speeches about organizations
const orgResponse = await fetch('/api/speeches/entities/search?entity=TBMM&entity_type=ORG');
```

### 4. Get Top Entities

Get the most frequently mentioned entities:

```javascript
// Top 50 entities overall
const topEntities = await fetch('/api/speeches/entities/top?limit=50');
const data = await topEntities.json();

// Top 20 people
const topPeople = await fetch('/api/speeches/entities/top?entity_type=PER&limit=20');

// Top locations
const topLocations = await fetch('/api/speeches/entities/top?entity_type=LOC');
```

## Frontend Examples

### React Component Example

```jsx
import React, { useState, useEffect } from 'react';

function SpeechWithEntities({ speechId }) {
  const [speech, setSpeech] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchSpeech() {
      const response = await fetch(`/api/speeches/${speechId}`);
      const data = await response.json();
      setSpeech(data);
      setLoading(false);
    }
    fetchSpeech();
  }, [speechId]);

  if (loading) return <div>Loading...</div>;
  if (!speech) return <div>Speech not found</div>;

  // Group entities by type
  const entitiesByType = {
    PER: speech.ner_entities?.filter(e => e.entity_group === 'PER') || [],
    LOC: speech.ner_entities?.filter(e => e.entity_group === 'LOC') || [],
    ORG: speech.ner_entities?.filter(e => e.entity_group === 'ORG') || []
  };

  return (
    <div>
      <h2>{speech.speech_title}</h2>
      <p>By: {speech.speech_giver}</p>
      
      {/* Display entities */}
      <div className="entities-section">
        <h3>Mentioned Entities</h3>
        
        {entitiesByType.PER.length > 0 && (
          <div className="entity-group">
            <h4>👤 People ({entitiesByType.PER.length})</h4>
            <ul>
              {entitiesByType.PER.map((entity, idx) => (
                <li key={idx}>
                  {entity.entity}
                  {entity.wikipedia_url && (
                    <a href={entity.wikipedia_url} target="_blank" rel="noopener">
                      📖
                    </a>
                  )}
                  <span className="frequency">({entity.frequency}x)</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {entitiesByType.LOC.length > 0 && (
          <div className="entity-group">
            <h4>📍 Locations ({entitiesByType.LOC.length})</h4>
            <ul>
              {entitiesByType.LOC.map((entity, idx) => (
                <li key={idx}>
                  {entity.entity}
                  {entity.wikipedia_url && (
                    <a href={entity.wikipedia_url} target="_blank" rel="noopener">
                      📖
                    </a>
                  )}
                  <span className="frequency">({entity.frequency}x)</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {entitiesByType.ORG.length > 0 && (
          <div className="entity-group">
            <h4>🏛️ Organizations ({entitiesByType.ORG.length})</h4>
            <ul>
              {entitiesByType.ORG.map((entity, idx) => (
                <li key={idx}>
                  {entity.entity}
                  {entity.wikipedia_url && (
                    <a href={entity.wikipedia_url} target="_blank" rel="noopener">
                      📖
                    </a>
                  )}
                  <span className="frequency">({entity.frequency}x)</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
```

### Entity Search Component

```jsx
function EntitySearch() {
  const [entity, setEntity] = useState('');
  const [entityType, setEntityType] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    const params = new URLSearchParams({ entity });
    if (entityType) params.append('entity_type', entityType);
    
    const response = await fetch(`/api/speeches/entities/search?${params}`);
    const data = await response.json();
    setResults(data);
    setLoading(false);
  };

  return (
    <div>
      <input
        type="text"
        value={entity}
        onChange={(e) => setEntity(e.target.value)}
        placeholder="Enter entity name..."
      />
      <select value={entityType} onChange={(e) => setEntityType(e.target.value)}>
        <option value="">All Types</option>
        <option value="PER">Person</option>
        <option value="LOC">Location</option>
        <option value="ORG">Organization</option>
      </select>
      <button onClick={handleSearch}>Search</button>

      {loading && <div>Loading...</div>}
      
      {results && (
        <div>
          <p>Found {results.total} speeches mentioning "{entity}"</p>
          {results.speeches.map(speech => (
            <div key={speech.id}>
              <h4>{speech.speech_title}</h4>
              <p>By: {speech.speech_giver} | Term: {speech.term}, Year: {speech.year}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

### Top Entities Widget

```jsx
function TopEntitiesWidget({ entityType, limit = 20 }) {
  const [entities, setEntities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTopEntities() {
      const params = new URLSearchParams({ limit: limit.toString() });
      if (entityType) params.append('entity_type', entityType);
      
      const response = await fetch(`/api/speeches/entities/top?${params}`);
      const data = await response.json();
      setEntities(data.entities);
      setLoading(false);
    }
    fetchTopEntities();
  }, [entityType, limit]);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="top-entities">
      <h3>Most Mentioned {entityType || 'Entities'}</h3>
      <ol>
        {entities.map((entity, idx) => (
          <li key={idx}>
            <span className="entity-name">{entity.entity}</span>
            <span className="entity-type">{entity.entity_group}</span>
            <span className="entity-count">{entity.count} mentions</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
```

### Highlight Entities in Speech Text

```jsx
function highlightEntities(text, entities) {
  if (!entities || entities.length === 0) return text;
  
  let highlightedText = text;
  entities.forEach(entity => {
    const regex = new RegExp(`\\b${entity.entity}\\b`, 'gi');
    const color = {
      'PER': '#4A90E2',
      'LOC': '#50C878',
      'ORG': '#FF6B6B'
    }[entity.entity_group] || '#999';
    
    highlightedText = highlightedText.replace(
      regex,
      `<mark style="background-color: ${color}; cursor: pointer;" title="${entity.entity_group} (confidence: ${(entity.confidence * 100).toFixed(1)}%)">$&</mark>`
    );
  });
  
  return highlightedText;
}

function SpeechContent({ speech }) {
  const highlightedContent = highlightEntities(
    speech.content || '',
    speech.ner_entities || []
  );

  return (
    <div 
      className="speech-content"
      dangerouslySetInnerHTML={{ __html: highlightedContent }}
    />
  );
}
```

## CSS Styling Example

```css
.entities-section {
  margin-top: 2rem;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 8px;
}

.entity-group {
  margin-bottom: 1.5rem;
}

.entity-group h4 {
  margin-bottom: 0.5rem;
  color: #333;
}

.entity-group ul {
  list-style: none;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.entity-group li {
  background: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.entity-group li a {
  margin-left: 0.25rem;
  text-decoration: none;
}

.frequency {
  color: #666;
  font-size: 0.875rem;
  margin-left: 0.25rem;
}

mark {
  padding: 2px 4px;
  border-radius: 3px;
  font-weight: 500;
}
```

## Use Cases

1. **Entity Tagging**: Display entities as tags/chips next to speeches
2. **Entity Search**: Allow users to search for speeches mentioning specific people, places, or organizations
3. **Entity Statistics**: Show which entities are mentioned most frequently
4. **Entity Highlighting**: Highlight entities in speech text with different colors
5. **Entity Links**: Link entities to Wikipedia pages when available
6. **Entity Filtering**: Filter speeches by entity type (show only speeches mentioning people, etc.)

## API Response Examples

### Speech with NER Entities

```json
{
  "id": "term27-year5-session18-17",
  "speech_giver": "Sefer Aycan",
  "term": 27,
  "year": 5,
  "ner_entities": [
    {
      "entity": "sefer aycan",
      "entity_group": "PER",
      "frequency": 1,
      "confidence": 0.998,
      "wikipedia_url": null
    },
    {
      "entity": "kahramanmaras",
      "entity_group": "LOC",
      "frequency": 1,
      "confidence": 0.999,
      "wikipedia_url": "https://tr.wikipedia.org/wiki/Kahramanmaraş"
    },
    {
      "entity": "saglık bakanlı",
      "entity_group": "ORG",
      "frequency": 2,
      "confidence": 0.881,
      "wikipedia_url": null
    }
  ]
}
```

### Top Entities Response

```json
{
  "entities": [
    {
      "entity": "tbmm",
      "entity_group": "ORG",
      "count": 15234
    },
    {
      "entity": "ankara",
      "entity_group": "LOC",
      "count": 8932
    },
    {
      "entity": "istanbul",
      "entity_group": "LOC",
      "count": 6543
    }
  ],
  "total": 50,
  "entity_type": "ALL"
}
```

## Tips

1. **Performance**: NER entities are included in search results, so no extra API calls needed
2. **Caching**: Consider caching top entities since they don't change frequently
3. **Filtering**: Use entity_type parameter to filter by PER, LOC, or ORG
4. **Wikipedia Links**: Check for `wikipedia_url` before showing Wikipedia icon
5. **Confidence Scores**: Use confidence scores to filter out low-confidence entities if needed
6. **Frequency**: Use frequency to show how often an entity appears in a speech

