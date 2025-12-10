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
            # Set compatibility mode for Elasticsearch 8.x server
            # This tells the 9.x client to use version 8 headers
            self._client = Elasticsearch(
                hosts=[ELASTICSEARCH_HOST],
                compatibility_version="8"
            )
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
            
            # Elasticsearch 8.x supports body parameter
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
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        size: int = 10,
        from_: int = 0
    ) -> Dict:
        """
        Search for speeches with various filters.
        Returns speech documents with all fields including session_date.
        
        Args:
            query_text: Full text search on content
            mp_name: Filter by MP name
            term: Filter by parliamentary term
            year: Filter by year
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
                    "match": {
                        "speech_giver": mp_name
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
            
            # Execute search
            response = client.search(
                index=ELASTICSEARCH_INDEX,
                body={
                    "query": query,
                    "size": size,
                    "from": from_,
                    "sort": [
                        {"session_date": {"order": "desc", "missing": "_last"}},
                        {"term": {"order": "desc"}},
                        {"year": {"order": "desc"}}
                    ]
                }
            )
            
            # Extract results
            total = response.get('hits', {}).get('total', {}).get('value', 0)
            hits = response.get('hits', {}).get('hits', [])
            
            speeches = []
            for hit in hits:
                source = hit['_source']
                speeches.append({
                    'id': hit['_id'],
                    'session_id': source.get('session_id'),
                    'term': source.get('term'),
                    'year': source.get('year'),
                    'file': source.get('file'),
                    'speech_no': source.get('speech_no'),
                    'province': source.get('province'),
                    'speech_giver': source.get('speech_giver'),
                    'political_party': source.get('political_party'),
                    'terms_served': source.get('terms_served'),
                    'speech_title': source.get('speech_title'),
                    'page_ref': source.get('page_ref'),
                    'content': source.get('content'),
                    'session_date': source.get('session_date')  # Include session_date
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


# Global instance
es_service = ElasticsearchService()

