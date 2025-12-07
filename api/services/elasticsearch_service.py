"""Service for querying Elasticsearch."""
from typing import Dict, List, Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, NotFoundError

from api.config import ELASTICSEARCH_HOST, ELASTICSEARCH_INDEX


class ElasticsearchService:
    """Service for Elasticsearch operations."""
    
    def __init__(self):
        self._client: Optional[Elasticsearch] = None
    
    def _get_client(self) -> Elasticsearch:
        """Get or create Elasticsearch client."""
        if self._client is None:
            self._client = Elasticsearch(hosts=[ELASTICSEARCH_HOST])
        return self._client
    
    def test_connection(self) -> bool:
        """Test Elasticsearch connection."""
        try:
            client = self._get_client()
            return client.ping()
        except Exception:
            return False
    
    def get_speech_activity_by_mp(self, mp_name: str) -> List[Dict]:
        """Get speech activity aggregated by year for an MP."""
        try:
            client = self._get_client()
            
            # Query for speeches by this MP, aggregated by year
            query = {
                "size": 0,  # We only want aggregations
                "query": {
                    "match": {
                        "speech_giver": mp_name
                    }
                },
                "aggs": {
                    "by_year": {
                        "terms": {
                            "field": "year",
                            "size": 100,  # Get all years
                            "order": {"_key": "asc"}
                        }
                    }
                }
            }
            
            # Elasticsearch 9.x supports body parameter
            response = client.search(index=ELASTICSEARCH_INDEX, body=query)
            
            # Extract year and count data
            activity = []
            if 'aggregations' in response and 'by_year' in response['aggregations']:
                buckets = response['aggregations']['by_year']['buckets']
                for bucket in buckets:
                    year = str(bucket['key'])
                    count = bucket['doc_count']
                    activity.append({
                        'year': year,
                        'speeches': count,
                        'laws': 0,  # Not implemented yet
                        'votes': 0  # Not implemented yet
                    })
            
            return sorted(activity, key=lambda x: int(x['year']))
            
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
            
            # Elasticsearch 9.x supports body parameter
            response = client.search(index=ELASTICSEARCH_INDEX, body=query)
            return response.get('hits', {}).get('total', {}).get('value', 0)
            
        except Exception as e:
            print(f"Error getting total speeches: {e}")
            return 0


# Global instance
es_service = ElasticsearchService()

