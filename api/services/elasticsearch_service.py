"""Service for querying Elasticsearch."""
from typing import Dict, List, Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, NotFoundError

from api.config import ELASTICSEARCH_HOST, ELASTICSEARCH_INDEX, TERM_YEAR_MAP


class ElasticsearchService:
    """Service for Elasticsearch operations."""
    
    def __init__(self):
        self._client: Optional[Elasticsearch] = None
    
    def _get_client(self) -> Elasticsearch:
        """Get or create Elasticsearch client."""
        if self._client is None:
            self._client = Elasticsearch(
                hosts=[ELASTICSEARCH_HOST]
            )
        return self._client
    
    def _clean_party_name(self, party_name: str) -> str:
        """
        Remove term prefix from party names.
        e.g., "27.dönem Cumhuriyet Halk Partisi" -> "Cumhuriyet Halk Partisi"
        """
        if not party_name:
            return party_name
        import re
        cleaned = re.sub(r'^\d+\.dönem\s+', '', party_name)
        return cleaned if cleaned else party_name
    
    def test_connection(self) -> bool:
        """Test Elasticsearch connection."""
        try:
            client = self._get_client()
            return client.ping()
        except Exception:
            return False
    
    def get_speech_activity_by_mp(self, mp_name: str) -> List[Dict]:
        """
        Get speech activity aggregated by term-year pairs for an MP.
        Returns real calendar years instead of term-year codes.
        """
        try:
            client = self._get_client()
            
            # Query for speeches by this MP, aggregated by term, then by year within term
            query = {
                "size": 0,  # We only want aggregations
                "query": {
                    "term": {
                        "speech_giver.keyword": mp_name
                    }
                },
                "aggs": {
                    "by_term": {
                        "terms": {
                            "field": "term",
                            "size": 50,
                            "order": {"_key": "asc"}
                        },
                        "aggs": {
                            "by_year": {
                                "terms": {
                                    "field": "year",
                                    "size": 10,
                                    "order": {"_key": "asc"}
                                }
                            }
                        }
                    }
                }
            }
            
            # Elasticsearch 8.x supports body parameter
            response = client.search(index=ELASTICSEARCH_INDEX, body=query)
            
            # Extract term-year pairs, convert to calendar years, and aggregate by calendar year
            # This handles cases where multiple term-year pairs map to the same calendar year
            activity_by_year = {}  # Dict to aggregate by calendar_year
            
            if 'aggregations' in response and 'by_term' in response['aggregations']:
                term_buckets = response['aggregations']['by_term']['buckets']
                
                for term_bucket in term_buckets:
                    term = int(term_bucket['key'])
                    
                    # Get calendar year range for this term
                    if term not in TERM_YEAR_MAP:
                        continue
                    
                    term_start, _ = TERM_YEAR_MAP[term]
                    
                    # Process each year within this term
                    if 'by_year' in term_bucket:
                        year_buckets = term_bucket['by_year']['buckets']
                        for year_bucket in year_buckets:
                            year_in_term = int(year_bucket['key'])
                            count = year_bucket['doc_count']
                            
                            # Calculate actual calendar year
                            calendar_year = term_start + (year_in_term - 1)
                            
                            # Aggregate by calendar year (combine multiple term-year pairs for same year)
                            if calendar_year not in activity_by_year:
                                activity_by_year[calendar_year] = {
                                    'term': term,  # Keep first term for reference
                                    'year_in_term': year_in_term,  # Keep first year_in_term
                                    'calendar_year': calendar_year,
                                    'year': str(calendar_year),
                                    'speeches': 0,
                                    'laws': 0,
                                    'votes': 0
                                }
                            
                            # Sum up speeches for this calendar year
                            activity_by_year[calendar_year]['speeches'] += count
            
            # Convert to list and sort by calendar year
            activity = list(activity_by_year.values())
            return sorted(activity, key=lambda x: x['calendar_year'])
            
        except ConnectionError:
            print(f"Error: Could not connect to Elasticsearch at {ELASTICSEARCH_HOST}")
            return []
        except NotFoundError:
            print(f"Error: Index {ELASTICSEARCH_INDEX} not found")
            return []
        except Exception as e:
            print(f"Error querying Elasticsearch: {e}")
            return []
    
    def get_total_speeches_by_mp(self, mp_name: str) -> int:
        """Get total number of speeches by an MP."""
        try:
            client = self._get_client()
            
            query = {
                "size": 0,
                "query": {
                    "match": {
                        "speech_giver": mp_name
                    }
                }
            }
            
            # Elasticsearch 8.x supports body parameter
            response = client.search(index=ELASTICSEARCH_INDEX, body=query)
            return response.get('hits', {}).get('total', {}).get('value', 0)
            
        except Exception as e:
            print(f"Error getting total speeches: {e}")
            return 0
    
    def search_speeches(
        self, 
        query_text: Optional[str] = None,
        mp_name: Optional[str] = None,
        term: Optional[int] = None,
        year: Optional[int] = None,
        topic_id: Optional[int] = None,
        topic_label: Optional[str] = None,
        province: Optional[str] = None,
        political_party: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        size: int = 10,
        from_: int = 0,
        sort_by: str = "date"
    ) -> Dict:
        """
        Search for speeches with various filters.
        Returns speech documents with all fields including session_date and topics.
        
        Args:
            query_text: Full text search on content
            mp_name: Filter by MP name
            term: Filter by parliamentary term
            year: Filter by year
            topic_id: Filter by topic ID (takes precedence over topic_label)
            topic_label: Filter by topic label
            from_date: Filter speeches from this date (format: dd.MM.yyyy)
            to_date: Filter speeches to this date (format: dd.MM.yyyy)
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Dictionary with 'total', 'speeches' list
        """
        try:
            client = self._get_client()
            
            # Build query
            must_clauses = []
            filter_clauses = []
            
            if query_text:
                must_clauses.append({
                    "match": {
                        "content": query_text
                    }
                })
            
            if mp_name:
                filter_clauses.append({
                    "term": {
                        "speech_giver.keyword": mp_name
                    }
                })
            
            if term is not None:
                filter_clauses.append({
                    "term": {"term": term}
                })
            
            if year is not None:
                filter_clauses.append({
                    "term": {"year": year}
                })
            
            # Topic filtering: topic_id takes precedence over topic_label
            if topic_id is not None:
                filter_clauses.append({
                    "term": {"hdbscan_topic_id": topic_id}
                })
            elif topic_label:
                filter_clauses.append({
                    "term": {"hdbscan_topic_label.keyword": topic_label}
                })
            
            if province:
                filter_clauses.append({
                    "term": {"province.keyword": province}
                })
            
            if political_party:
                filter_clauses.append({
                    "term": {"political_party_at_time.keyword": political_party}
                })
            
            # Date range filter
            if from_date or to_date:
                date_range = {"session_date": {}}
                if from_date:
                    date_range["session_date"]["gte"] = from_date
                if to_date:
                    date_range["session_date"]["lte"] = to_date
                filter_clauses.append({"range": date_range})
            
            # Construct the query
            if must_clauses or filter_clauses:
                query = {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}],
                        "filter": filter_clauses
                    }
                }
            else:
                query = {"match_all": {}}
            
            # Determine sort order
            if sort_by == "relevance" and query_text:
                sort_config = [{"_score": {"order": "desc"}}]
            else:
                # Default: sort by term and year (numeric, fast)
                sort_config = [
                    {"term": {"order": "desc"}},
                    {"year": {"order": "desc"}}
                ]
            
            # Execute search
            response = client.search(
                index=ELASTICSEARCH_INDEX,
                body={
                    "query": query,
                    "size": size,
                    "from": from_,
                    "sort": sort_config
                }
            )
            
            # Extract results
            total = response.get('hits', {}).get('total', {}).get('value', 0)
            hits = response.get('hits', {}).get('hits', [])
            
            speeches = []
            for hit in hits:
                source = hit['_source']
                
                # Get political_party_at_time (clean party name without term prefix)
                political_party = source.get('political_party_at_time') or source.get('political_party')
                if isinstance(political_party, list):
                    political_party = political_party[0] if political_party else None
                # Clean party name (remove term prefix if present)
                political_party = self._clean_party_name(political_party) if political_party else None
                
                terms_served = source.get('terms_served')
                if isinstance(terms_served, list):
                    terms_served = ', '.join(map(str, terms_served)) if terms_served else None
                
                speeches.append({
                    'id': hit['_id'],
                    'session_id': source.get('session_id'),
                    'term': source.get('term'),
                    'year': source.get('year'),
                    'file': source.get('file'),
                    'speech_no': source.get('speech_no'),
                    'province': source.get('province'),
                    'speech_giver': source.get('speech_giver'),
                    'political_party': political_party,
                    'terms_served': terms_served,
                    'speech_title': source.get('speech_title'),
                    'page_ref': source.get('page_ref'),
                    'content': source.get('content'),
                    'session_date': source.get('session_date'),
                    'hdbscan_topic_id': source.get('hdbscan_topic_id'),
                    'hdbscan_topic_label': source.get('hdbscan_topic_label'),
                    'keywords': source.get('keywords', []),
                    'keywords_str': source.get('keywords_str'),
                    'ner_entities': source.get('ner_entities', [])
                })
            
            return {
                'total': total,
                'speeches': speeches
            }
            
        except Exception as e:
            print(f"Error searching speeches: {e}")
            return {'total': 0, 'speeches': []}
    
    def get_speeches_by_mp(self, mp_name: str, size: int = 100) -> List[Dict]:
        """
        Get speeches by an MP with all fields including session_date.
        Convenience method that wraps search_speeches.
        
        Args:
            mp_name: Name of the MP
            size: Maximum number of speeches to return
            
        Returns:
            List of speech dictionaries with session_date
        """
        result = self.search_speeches(mp_name=mp_name, size=size)
        return result.get('speeches', [])
    
    def get_topic_statistics(self) -> List[Dict]:
        """
        Get aggregated statistics for all HDBSCAN topics.
        Filters out outliers (topic_id=-1) and extraction errors (topic_id=1).
        
        Returns:
            List of topic statistics with counts and labels
        """
        try:
            client = self._get_client()
            
            query = {
                "size": 0,
                "query": {
                    "bool": {
                        "must": [
                            {"exists": {"field": "hdbscan_topic_id"}}
                        ],
                        "must_not": [
                            {"term": {"hdbscan_topic_id": -1}},  # Exclude outliers
                            {"term": {"hdbscan_topic_id": 1}}    # Exclude extraction errors
                        ]
                    }
                },
                "aggs": {
                    "topics": {
                        "terms": {
                            "field": "hdbscan_topic_id",
                            "size": 1000,
                            "order": {"_count": "desc"}
                        },
                        "aggs": {
                            "topic_label": {
                                "terms": {
                                    "field": "hdbscan_topic_label.keyword",
                                    "size": 1
                                }
                            }
                        }
                    }
                }
            }
            
            response = client.search(index=ELASTICSEARCH_INDEX, body=query)
            
            topics = []
            if 'aggregations' in response and 'topics' in response['aggregations']:
                buckets = response['aggregations']['topics']['buckets']
                for bucket in buckets:
                    topic_id = bucket['key']
                    count = bucket['doc_count']
                    
                    # Get topic label
                    label_buckets = bucket.get('topic_label', {}).get('buckets', [])
                    topic_label = label_buckets[0]['key'] if label_buckets else f"Topic {topic_id}"
                    
                    topics.append({
                        'topic_id': topic_id,
                        'topic_label': topic_label,
                        'speech_count': count
                    })
            
            return topics
            
        except Exception as e:
            print(f"Error getting topic statistics: {e}")
            return []
    
    def get_topics_by_mp(self, mp_name: str, top_n: int = 4) -> List[Dict]:
        """
        Get topic distribution for a specific MP using HDBSCAN topics.
        Filters out outliers (topic_id=-1) and extraction errors (topic_id=1).
        
        Args:
            mp_name: Name of the MP
            top_n: Number of top topics to return
            
        Returns:
            List of topics with counts and percentages for this MP
        """
        try:
            client = self._get_client()
            
            query = {
                "size": 0,
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"speech_giver.keyword": mp_name}},
                            {"exists": {"field": "hdbscan_topic_id"}}
                        ],
                        "must_not": [
                            {"term": {"hdbscan_topic_id": -1}},  # Exclude outliers
                            {"term": {"hdbscan_topic_id": 1}}    # Exclude extraction errors
                        ]
                    }
                },
                "aggs": {
                    "topics": {
                        "terms": {
                            "field": "hdbscan_topic_id",
                            "size": top_n,
                            "order": {"_count": "desc"}
                        },
                        "aggs": {
                            "topic_label": {
                                "terms": {
                                    "field": "hdbscan_topic_label.keyword",
                                    "size": 1
                                }
                            }
                        }
                    }
                }
            }
            
            response = client.search(index=ELASTICSEARCH_INDEX, body=query)
            
            # Calculate total speeches for percentage
            total_hits = response.get('hits', {}).get('total', {})
            if isinstance(total_hits, dict):
                total_speeches = total_hits.get('value', 0)
            else:
                total_speeches = total_hits
            
            topics = []
            if 'aggregations' in response and 'topics' in response['aggregations']:
                buckets = response['aggregations']['topics']['buckets']
                for bucket in buckets:
                    topic_id = bucket['key']
                    count = bucket['doc_count']
                    
                    # Get topic label
                    label_buckets = bucket.get('topic_label', {}).get('buckets', [])
                    topic_label = label_buckets[0]['key'] if label_buckets else f"Topic {topic_id}"
                    
                    # Calculate percentage
                    percentage = round((count / total_speeches * 100), 1) if total_speeches > 0 else 0.0
                    
                    topics.append({
                        'name': topic_label,
                        'count': count,
                        'percentage': percentage,
                        'topic_id': topic_id
                    })
            
            return topics
            
        except Exception as e:
            print(f"Error getting topics for MP: {e}")
            return []
    
    def get_topics_by_party_for_mp(self, mp_name: str, top_n: int = 10) -> Dict[str, List[Dict]]:
        """
        Get topics for an MP grouped by political party using HDBSCAN topics.
        Uses political_party_at_time field for accurate party association.
        Filters out outliers (topic_id=-1) and extraction errors (topic_id=1).
        
        Args:
            mp_name: Name of the MP
            top_n: Maximum number of topics to return per party
            
        Returns:
            Dictionary mapping party name to list of topics: {party_name: [{name, count, percentage}, ...]}
        """
        try:
            client = self._get_client()
            
            query = {
                "size": 0,
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"speech_giver.keyword": mp_name}},
                            {"exists": {"field": "hdbscan_topic_id"}},
                            {"exists": {"field": "political_party_at_time"}}
                        ],
                        "must_not": [
                            {"term": {"hdbscan_topic_id": -1}},  # Exclude outliers
                            {"term": {"hdbscan_topic_id": 1}}    # Exclude extraction errors
                        ]
                    }
                },
                "aggs": {
                    "parties": {
                        "terms": {
                            "field": "political_party_at_time.keyword",
                            "size": 50
                        },
                        "aggs": {
                            "topics": {
                                "terms": {
                                    "field": "hdbscan_topic_id",
                                    "size": top_n,
                                    "order": {"_count": "desc"}
                                },
                                "aggs": {
                                    "topic_label": {
                                        "terms": {
                                            "field": "hdbscan_topic_label.keyword",
                                            "size": 1
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            response = client.search(index=ELASTICSEARCH_INDEX, body=query)
            
            topics_by_party = {}
            if 'aggregations' in response and 'parties' in response['aggregations']:
                party_buckets = response['aggregations']['parties']['buckets']
                
                for party_bucket in party_buckets:
                    party_name = party_bucket['key']
                    party_total_speeches = party_bucket['doc_count']
                    
                    topics = []
                    if 'topics' in party_bucket:
                        topic_buckets = party_bucket['topics']['buckets']
                        
                        for topic_bucket in topic_buckets:
                            topic_id = topic_bucket['key']
                            count = topic_bucket['doc_count']
                            
                            # Get topic label
                            label_buckets = topic_bucket.get('topic_label', {}).get('buckets', [])
                            topic_label = label_buckets[0]['key'] if label_buckets else f"Topic {topic_id}"
                            
                            # Calculate percentage within this party
                            percentage = round((count / party_total_speeches * 100), 1) if party_total_speeches > 0 else 0.0
                            
                            topics.append({
                                'name': topic_label,
                                'count': count,
                                'percentage': percentage,
                                'topic_id': topic_id
                            })
                    
                    if topics:  # Only add if there are topics
                        topics_by_party[party_name] = topics
            
            return topics_by_party
            
        except Exception as e:
            print(f"Error getting topics by party for MP: {e}")
            return {}
    
    def get_speech_by_id(self, speech_id: str) -> Optional[Dict]:
        """
        Get a single speech document by ID.
        
        Args:
            speech_id: The document ID
            
        Returns:
            Speech document dict or None if not found
        """
        try:
            client = self._get_client()
            response = client.get(index=ELASTICSEARCH_INDEX, id=speech_id)
            
            if response.get('found'):
                source = response['_source']
                
                # Get political_party_at_time (clean party name without term prefix)
                political_party = source.get('political_party_at_time') or source.get('political_party')
                if isinstance(political_party, list):
                    political_party = political_party[0] if political_party else None
                # Clean party name (remove term prefix if present)
                political_party = self._clean_party_name(political_party) if political_party else None
                
                terms_served = source.get('terms_served')
                if isinstance(terms_served, list):
                    terms_served = ', '.join(map(str, terms_served)) if terms_served else None
                
                return {
                    'id': response['_id'],
                    'session_id': source.get('session_id'),
                    'term': source.get('term'),
                    'year': source.get('year'),
                    'file': source.get('file'),
                    'speech_no': source.get('speech_no'),
                    'province': source.get('province'),
                    'speech_giver': source.get('speech_giver'),
                    'political_party': political_party,
                    'terms_served': terms_served,
                    'speech_title': source.get('speech_title'),
                    'page_ref': source.get('page_ref'),
                    'content': source.get('content'),
                    'session_date': source.get('session_date'),
                    'hdbscan_topic_id': source.get('hdbscan_topic_id'),
                    'hdbscan_topic_label': source.get('hdbscan_topic_label'),
                    'keywords': source.get('keywords', []),
                    'keywords_str': source.get('keywords_str'),
                    'ner_entities': source.get('ner_entities', [])
                }
            return None
            
        except NotFoundError:
            return None
        except Exception as e:
            print(f"Error getting speech by ID: {e}")
            return None
    
    def get_facets(self) -> Dict:
        """
        Get aggregated facets for search filters.
        
        Returns:
            Dict with terms, years, parties, topics, provinces counts
        """
        try:
            client = self._get_client()
            
            query = {
                "size": 0,
                "aggs": {
                    "terms": {
                        "terms": {"field": "term", "size": 50, "order": {"_key": "desc"}}
                    },
                    "years": {
                        "terms": {"field": "year", "size": 10, "order": {"_key": "desc"}}
                    },
                    "parties": {
                        "terms": {"field": "political_party.keyword", "size": 50}
                    },
                    "topics": {
                        "terms": {"field": "hdbscan_topic_id", "size": 200}
                    },
                    "provinces": {
                        "terms": {"field": "province.keyword", "size": 100}
                    }
                }
            }
            
            response = client.search(index=ELASTICSEARCH_INDEX, body=query)
            
            facets = {
                "terms": [],
                "years": [],
                "parties": [],
                "topics": [],
                "provinces": []
            }
            
            aggs = response.get('aggregations', {})
            
            for key in ['terms', 'years', 'parties', 'topics', 'provinces']:
                if key in aggs:
                    facets[key] = [
                        {"value": bucket['key'], "count": bucket['doc_count']}
                        for bucket in aggs[key].get('buckets', [])
                    ]
            
            return facets
            
        except Exception as e:
            print(f"Error getting facets: {e}")
            return {"terms": [], "years": [], "parties": [], "topics": [], "provinces": []}
    
    def get_filters(self) -> Dict:
        """
        Get filter options as flat arrays (for frontend dropdown filters).
        Topics are returned as objects with id and label.
        
        Returns:
            Dict with parties, terms, years, speakers as flat arrays, topics as objects with id/label
        """
        try:
            client = self._get_client()
            
            query = {
                "size": 0,
                "query": {
                    "bool": {
                        "must_not": [
                            {"term": {"hdbscan_topic_id": -1}},  # Exclude outliers
                            {"term": {"hdbscan_topic_id": 1}}    # Exclude extraction errors
                        ]
                    }
                },
                "aggs": {
                    "terms": {
                        "terms": {"field": "term", "size": 50, "order": {"_key": "desc"}}
                    },
                    "years": {
                        "terms": {"field": "year", "size": 10, "order": {"_key": "asc"}}
                    },
                    "parties": {
                        "terms": {"field": "political_party_at_time.keyword", "size": 100}
                    },
                    "speakers": {
                        "terms": {"field": "speech_giver.keyword", "size": 1000}
                    },
                    "topics": {
                        "terms": {
                            "field": "hdbscan_topic_id",
                            "size": 200,
                            "order": {"_count": "desc"}
                        },
                        "aggs": {
                            "topic_label": {
                                "terms": {
                                    "field": "hdbscan_topic_label.keyword",
                                    "size": 1
                                }
                            }
                        }
                    }
                }
            }
            
            response = client.search(index=ELASTICSEARCH_INDEX, body=query)
            aggs = response.get('aggregations', {})
            
            filters = {
                "parties": [],
                "terms": [],
                "years": [],
                "speakers": [],
                "topics": []
            }
            
            # Extract values as flat arrays for most filters
            for key in ['parties', 'terms', 'years', 'speakers']:
                if key in aggs:
                    filters[key] = [bucket['key'] for bucket in aggs[key].get('buckets', [])]
            
            # Special handling for topics: extract id and label
            if 'topics' in aggs:
                topic_buckets = aggs['topics'].get('buckets', [])
                topics_list = []
                for bucket in topic_buckets:
                    topic_id = bucket['key']
                    # Get topic label from nested aggregation
                    label_buckets = bucket.get('topic_label', {}).get('buckets', [])
                    topic_label = label_buckets[0]['key'] if label_buckets else f"Topic {topic_id}"
                    
                    topics_list.append({
                        "id": topic_id,
                        "label": topic_label
                    })
                filters['topics'] = topics_list
            
            return filters
            
        except Exception as e:
            print(f"Error getting filters: {e}")
            return {"parties": [], "terms": [], "years": [], "speakers": [], "topics": []}
    
    def get_total_count(self) -> int:
        """
        Get total number of speeches in the index.
        
        Returns:
            Total count as integer
        """
        try:
            client = self._get_client()
            response = client.count(index=ELASTICSEARCH_INDEX)
            return response.get('count', 0)
        except Exception as e:
            print(f"Error getting count: {e}")
            return 0
    
    def get_index_stats(self) -> Dict:
        """
        Get index statistics.
        
        Returns:
            Dict with total counts and ranges
        """
        try:
            client = self._get_client()
            
            # Get total count
            count_response = client.count(index=ELASTICSEARCH_INDEX)
            total_speeches = count_response.get('count', 0)
            
            # Get aggregations for stats
            # Try session_id.keyword with cardinality first, fallback to terms aggregation if it fails
            query = {
                "size": 0,
                "aggs": {
                    "unique_sessions": {
                        "cardinality": {"field": "session_id.keyword"}
                    },
                    "unique_mps": {
                        "cardinality": {"field": "speech_giver.keyword"}
                    },
                    "unique_topics": {
                        "cardinality": {"field": "hdbscan_topic_id"}
                    },
                    "term_stats": {
                        "stats": {"field": "term"}
                    },
                    "year_stats": {
                        "stats": {"field": "year"}
                    }
                }
            }
            
            # Try the query with cardinality on session_id.keyword
            try:
                response = client.search(index=ELASTICSEARCH_INDEX, body=query)
                aggs = response.get('aggregations', {})
                total_sessions = aggs.get('unique_sessions', {}).get('value', 0)
            except Exception as session_error:
                # If cardinality fails, try with terms aggregation instead
                print(f"Warning: Cardinality on session_id.keyword failed, using terms aggregation: {session_error}")
                query["aggs"].pop("unique_sessions")
                query["aggs"]["unique_sessions_terms"] = {
                    "terms": {"field": "session_id.keyword", "size": 10000}
                }
                response = client.search(index=ELASTICSEARCH_INDEX, body=query)
                aggs = response.get('aggregations', {})
                # Count unique buckets from terms aggregation
                total_sessions = len(aggs.get('unique_sessions_terms', {}).get('buckets', []))
            
            # Get MPs from term 17+ (using same filter as MP listing)
            query_term_17 = {
                "size": 0,
                "query": {
                    "range": {
                        "term": {"gte": 17}
                    }
                },
                "aggs": {
                    "unique_mps_term_17": {
                        "cardinality": {"field": "speech_giver.keyword"}
                    }
                }
            }
            
            response_term_17 = client.search(index=ELASTICSEARCH_INDEX, body=query_term_17)
            aggs_term_17 = response_term_17.get('aggregations', {})
            
            term_stats = aggs.get('term_stats', {})
            year_stats = aggs.get('year_stats', {})
            
            return {
                "total_speeches": total_speeches,
                "total_sessions": total_sessions,
                "total_mps": aggs.get('unique_mps', {}).get('value', 0),
                "total_mps_from_term_17": aggs_term_17.get('unique_mps_term_17', {}).get('value', 0),
                "total_topics": aggs.get('unique_topics', {}).get('value', 0),
                "terms_range": {
                    "min": int(term_stats.get('min', 0)) if term_stats.get('min') else 0,
                    "max": int(term_stats.get('max', 0)) if term_stats.get('max') else 0
                },
                "years_range": {
                    "min": int(year_stats.get('min', 0)) if year_stats.get('min') else 0,
                    "max": int(year_stats.get('max', 0)) if year_stats.get('max') else 0
                }
            }
            
        except Exception as e:
            import traceback
            error_msg = f"Error getting index stats: {e}"
            print(error_msg)
            print(traceback.format_exc())
            print(f"Elasticsearch host: {ELASTICSEARCH_HOST}")
            print(f"Elasticsearch index: {ELASTICSEARCH_INDEX}")
            return {
                "total_speeches": 0,
                "total_sessions": 0,
                "total_mps": 0,
                "total_mps_from_term_17": 0,
                "total_topics": 0,
                "terms_range": {"min": 0, "max": 0},
                "years_range": {"min": 0, "max": 0}
            }
    
    def search_by_entity(self, entity_name: str, entity_type: Optional[str] = None, size: int = 20, from_: int = 0) -> Dict:
        """
        Search speeches by NER entity name and optionally by entity type.
        
        Args:
            entity_name: Name of the entity to search for
            entity_type: Optional entity type filter (PER, LOC, ORG)
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Dictionary with 'total', 'speeches' list
        """
        try:
            client = self._get_client()
            
            # Build nested query for entity search
            nested_query = {
                "nested": {
                    "path": "ner_entities",
                    "query": {
                        "bool": {
                            "must": [
                                {"match": {"ner_entities.entity": entity_name}}
                            ]
                        }
                    }
                }
            }
            
            # Add entity type filter if provided
            if entity_type:
                nested_query["nested"]["query"]["bool"]["must"].append(
                    {"term": {"ner_entities.entity_group": entity_type}}
                )
            
            query = {
                "query": nested_query,
                "size": size,
                "from": from_,
                "sort": [{"term": {"order": "desc"}}, {"year": {"order": "desc"}}]
            }
            
            response = client.search(index=ELASTICSEARCH_INDEX, **query)
            
            total = response.get('hits', {}).get('total', {}).get('value', 0)
            hits = response.get('hits', {}).get('hits', [])
            
            speeches = []
            for hit in hits:
                source = hit['_source']
                political_party = source.get('political_party_at_time') or source.get('political_party')
                if isinstance(political_party, list):
                    political_party = political_party[0] if political_party else None
                political_party = self._clean_party_name(political_party) if political_party else None
                
                terms_served = source.get('terms_served')
                if isinstance(terms_served, list):
                    terms_served = ', '.join(map(str, terms_served)) if terms_served else None
                
                speeches.append({
                    'id': hit['_id'],
                    'session_id': source.get('session_id'),
                    'term': source.get('term'),
                    'year': source.get('year'),
                    'file': source.get('file'),
                    'speech_no': source.get('speech_no'),
                    'province': source.get('province'),
                    'speech_giver': source.get('speech_giver'),
                    'political_party': political_party,
                    'terms_served': terms_served,
                    'speech_title': source.get('speech_title'),
                    'page_ref': source.get('page_ref'),
                    'content': source.get('content'),
                    'session_date': source.get('session_date'),
                    'hdbscan_topic_id': source.get('hdbscan_topic_id'),
                    'hdbscan_topic_label': source.get('hdbscan_topic_label'),
                    'keywords': source.get('keywords', []),
                    'keywords_str': source.get('keywords_str'),
                    'ner_entities': source.get('ner_entities', [])
                })
            
            return {
                'total': total,
                'speeches': speeches
            }
            
        except Exception as e:
            print(f"Error searching by entity: {e}")
            return {'total': 0, 'speeches': []}
    
    def get_top_entities(self, entity_type: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """
        Get top entities by frequency across all speeches.
        
        Args:
            entity_type: Optional filter by entity type (PER, LOC, ORG)
            limit: Number of top entities to return
            
        Returns:
            List of entities with counts: [{"entity": "...", "entity_group": "...", "count": 123}, ...]
        """
        try:
            client = self._get_client()
            
            # Build aggregation query
            aggs = {
                "entities": {
                    "nested": {"path": "ner_entities"},
                    "aggs": {
                        "entity_names": {
                            "terms": {
                                "field": "ner_entities.entity",
                                "size": limit,
                                "order": {"_count": "desc"}
                            },
                            "aggs": {
                                "entity_type": {
                                    "terms": {
                                        "field": "ner_entities.entity_group",
                                        "size": 1
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            # Add entity type filter if provided
            query = {"match_all": {}}
            if entity_type:
                query = {
                    "nested": {
                        "path": "ner_entities",
                        "query": {
                            "term": {"ner_entities.entity_group": entity_type}
                        }
                    }
                }
            
            es_query = {
                "size": 0,
                "query": query,
                "aggs": aggs
            }
            
            response = client.search(index=ELASTICSEARCH_INDEX, **es_query)
            
            entities = []
            if 'aggregations' in response and 'entities' in response['aggregations']:
                buckets = response['aggregations']['entities']['entity_names']['buckets']
                for bucket in buckets:
                    entity_name = bucket['key']
                    count = bucket['doc_count']
                    
                    # Get entity type
                    entity_type_buckets = bucket.get('entity_type', {}).get('buckets', [])
                    entity_group = entity_type_buckets[0]['key'] if entity_type_buckets else "UNKNOWN"
                    
                    entities.append({
                        'entity': entity_name,
                        'entity_group': entity_group,
                        'count': count
                    })
            
            return entities
            
        except Exception as e:
            print(f"Error getting top entities: {e}")
            return []


# Global instance
es_service = ElasticsearchService()

