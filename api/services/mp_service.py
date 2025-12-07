"""Service for combining MP data from various sources."""
from typing import Dict, List, Optional

from api.services.csv_service import csv_service
from api.services.elasticsearch_service import es_service


class MPService:
    """Service for MP data operations."""
    
    def get_all_mps(self) -> List[Dict]:
        """Get list of all MPs."""
        mp_lookup = csv_service.load_mp_lookup()
        
        mps = []
        for mp_id, mp_data in mp_lookup.items():
            mps.append({
                'id': mp_id,
                'name': mp_data['name'],
                'party': mp_data['party']
            })
        
        return sorted(mps, key=lambda x: x['name'])
    
    def get_mp_detail(self, mp_id: str) -> Optional[Dict]:
        """Get complete MP detail information."""
        mp_data = csv_service.get_mp_by_id(mp_id)
        
        if not mp_data:
            return None
        
        mp_name = mp_data['name']
        
        # Get topics
        topics_data = csv_service.get_topics_for_mp(mp_name, top_n=4)
        
        # Get activity from Elasticsearch
        activity_data = es_service.get_speech_activity_by_mp(mp_name)
        
        # Format terms
        terms = csv_service.format_terms(mp_data['terms'])
        
        # Generate stance description (placeholder for now)
        stance = self._generate_stance(mp_data['party'], topics_data)
        
        return {
            'name': mp_name,
            'party': mp_data['party'],
            'terms': terms,
            'topics': topics_data,
            'activity': activity_data,
            'stance': stance
        }
    
    def _generate_stance(self, party: str, topics: List[Dict]) -> str:
        """Generate a stance description based on party and topics."""
        if not topics:
            return f"Member of {party} with parliamentary activity."
        
        top_topic = topics[0]['name'] if topics else "various topics"
        return f"Member of {party} with focus on {top_topic} and related parliamentary matters."


# Global instance
mp_service = MPService()

