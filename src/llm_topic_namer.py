"""
LLM-based Topic Name Generator using Groq API

This module generates human-readable topic names from BERTopic's keyword-based labels
using Groq's LLM API with Turkish language support.
"""

import os
import sys
import time
import csv
from typing import Dict, List, Optional, Tuple
from elasticsearch import Elasticsearch, helpers
import re

from dotenv import load_dotenv
load_dotenv()

class GroqTopicNamer:
    """Service for generating readable topic names using Groq LLM."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq topic namer.
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            model: Groq model to use (default: llama-3.1-70b-versatile)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = os.getenv("GROQ_MODEL")
        
        if not self.api_key:
            raise ValueError(
                "Groq API key not found. Set GROQ_API_KEY environment variable or pass api_key parameter."
            )
        
        # Import groq here to give clear error if not installed
        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "groq package not installed. Install with: pip install groq"
            )
    
    def _build_prompt(self, keywords: str, representative_docs: List[str]) -> str:
        """
        Build Turkish prompt for LLM.
        
        Args:
            keywords: Comma-separated keywords from BERTopic
            representative_docs: List of representative speech excerpts
            
        Returns:
            Formatted prompt string
        """
        # Limit docs to first 2-3 and truncate each to ~200 chars
        docs_text = ""
        for i, doc in enumerate(representative_docs[:3], 1):
            truncated = doc[:200] if len(doc) > 200 else doc
            docs_text += f"{i}. {truncated}...\n\n"
        
        prompt = f"""Sen Türkiye Büyük Millet Meclisi konuşmalarını analiz eden bir uzmansın.
Aşağıdaki anahtar kelimeler ve örnek konuşma metinlerinden yola çıkarak,
bu konuyu en iyi tanımlayan kısa ve anlamlı bir başlık oluştur. başlığı doğrudan cevap olarak ver açıklama yapma. Örnek başlıklar : Ekonomi ve Bütçe Politikaları, Eğitim Sistemi ve Öğretmenlik, Sağlık Hizmetleri ve Tedavi, Güvenlik ve Terörle Mücadele, vb.

Anahtar Kelimeler: {keywords}

Örnek Konuşmalar:
{docs_text}

Sadece başlık ver, açıklama yapma. Başlık Türkçe olmalı ve en fazla 5 kelime olmalı.
Başlık:"""
        
        return prompt
    
    def generate_topic_name(
        self, 
        topic_id: int, 
        keywords: str, 
        representative_docs: List[str],
        max_retries: int = 3
    ) -> str:
        """
        Generate a readable topic name using Groq LLM.
        
        Args:
            topic_id: Topic ID
            keywords: Comma-separated keywords
            representative_docs: List of representative speech excerpts
            max_retries: Maximum retry attempts on failure
            
        Returns:
            Human-readable topic name in Turkish
        """
        # Build prompt
        prompt = self._build_prompt(keywords, representative_docs)
        
        # Try to generate name with retries
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Sen Türkçe konuşan bir meclis uzmanısın. Kısa, açık ve anlamlı başlıklar oluşturursun."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,  # Lower temperature for more consistent names
                    max_tokens=50,  # Short responses
                    top_p=1,
                    stream=False
                )
                
                # Extract and clean the response
                generated_name = response.choices[0].message.content.strip()
                
                # Clean up the response
                generated_name = self._clean_topic_name(generated_name)
                
                # Validate
                if generated_name and len(generated_name) > 5:
                    return generated_name
                else:
                    print(f"   ⚠️  Generated name too short for topic {topic_id}, retrying...")
                    
            except Exception as e:
                print(f"   ⚠️  Attempt {attempt + 1} failed for topic {topic_id}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
        
        # Fallback to formatted keywords if all retries fail
        print(f"   ⚠️  All retries failed for topic {topic_id}, using fallback")
        return self._format_keywords_fallback(keywords)
    
    def _clean_topic_name(self, name: str) -> str:
        """
        Clean and validate generated topic name.
        
        Args:
            name: Raw generated name
            
        Returns:
            Cleaned name
        """
        # Remove common prefixes/suffixes
        name = re.sub(r'^(Başlık:|Konu:|Topic:)\s*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'["\']', '', name)  # Remove quotes
        name = name.strip()
        
        # Capitalize first letter of each word properly
        words = name.split()
        cleaned_words = []
        for word in words:
            # Keep Turkish special characters
            if word and len(word) > 1:
                cleaned_words.append(word[0].upper() + word[1:].lower())
            elif word:
                cleaned_words.append(word.upper())
        
        return ' '.join(cleaned_words)
    
    def _format_keywords_fallback(self, keywords: str) -> str:
        """
        Format keywords as fallback when LLM fails.
        
        Args:
            keywords: Comma-separated keywords
            
        Returns:
            Formatted string
        """
        words = [w.strip().capitalize() for w in keywords.split(',')[:4]]
        return ' ve '.join(words) if len(words) <= 3 else ' '.join(words[:3])
    
    def process_topic_details_csv(self, csv_path: str) -> Dict[int, str]:
        """
        Process topic_details.csv and generate names for all topics.
        
        Args:
            csv_path: Path to topic_details.csv
            
        Returns:
            Dictionary mapping topic_id to readable name
        """
        print(f"\n🤖 Generating readable topic names with Groq LLM...")
        print(f"   Model: {self.model}")
        
        topic_mapping = {} 
        
        try:
            # Increase CSV field size limit to handle large Representative_Docs fields
            import sys
            maxInt = sys.maxsize
            while True:
                try:
                    csv.field_size_limit(maxInt)
                    break
                except OverflowError:
                    maxInt = int(maxInt / 10)
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                topics = list(reader)
            
            total = len(topics)
            print(f"   Processing {total} topics...")
            
            for idx, row in enumerate(topics, 1):
                topic_id = int(row['Topic'])
                
                # Skip outliers
                if topic_id == -1:
                    print(f"   [{idx}/{total}] Skipping outlier topic -1")
                    continue
                
                keywords = row.get('Keywords', '')
                rep_docs_str = row.get('Representative_Docs', '')
                
                # Truncate to first 3000 chars to avoid field size issues and reduce LLM token usage
                if len(rep_docs_str) > 3000:
                    rep_docs_str = rep_docs_str[:3000]
                
                # Parse representative docs (they're stored as a string list)
                try:
                    # Remove brackets and split by quote-comma-quote pattern
                    rep_docs_str = rep_docs_str.strip('[]')
                    if rep_docs_str:
                        # Simple parsing - split by ', ' and clean quotes
                        rep_docs = [doc.strip(' "\'') for doc in rep_docs_str.split('", "')]
                        rep_docs = [doc for doc in rep_docs if doc]  # Remove empty
                    else:
                        rep_docs = []
                except:
                    rep_docs = []
                
                # Generate name
                print(f"   [{idx}/{total}] Topic {topic_id}: Generating name...")
                readable_name = self.generate_topic_name(topic_id, keywords, rep_docs)
                topic_mapping[topic_id] = readable_name
                
                print(f"   ✅ Topic {topic_id}: \"{readable_name}\"")
                
                # Small delay to avoid rate limits
                time.sleep(0.1)
            
            print(f"\n✅ Successfully generated {len(topic_mapping)} topic names")
            return topic_mapping
            
        except FileNotFoundError:
            print(f"❌ Error: topic_details.csv not found at {csv_path}")
            return {}
        except Exception as e:
            print(f"❌ Error processing topics: {e}")
            return {}


def update_elasticsearch_topic_labels(
    es: Elasticsearch, 
    topic_mapping: Dict[int, str],
    index: str = "parliament_speeches"
) -> int:
    """
    Bulk update Elasticsearch documents with readable topic names.
    
    Args:
        es: Elasticsearch client
        topic_mapping: Dictionary mapping topic_id to readable name
        index: Elasticsearch index name
        
    Returns:
        Number of documents updated
    """
    print(f"\n💾 Updating Elasticsearch with readable topic names...")
    
    total_updated = 0
    
    for topic_id, readable_name in topic_mapping.items():
        try:
            # Update all documents with this topic_id
            response = es.update_by_query(
                index=index,
                body={
                    "script": {
                        "source": "ctx._source.topic_label = params.new_label",
                        "lang": "painless",
                        "params": {
                            "new_label": readable_name
                        }
                    },
                    "query": {
                        "term": {"topic_id": topic_id}
                    }
                },
                conflicts='proceed',
                refresh=True
            )
            
            updated = response.get('updated', 0)
            total_updated += updated
            
            if updated > 0:
                print(f"   ✅ Topic {topic_id}: Updated {updated:,} documents to \"{readable_name}\"")
            
        except Exception as e:
            print(f"   ❌ Error updating topic {topic_id}: {e}")
            continue
    
    print(f"\n✅ Total documents updated: {total_updated:,}")
    return total_updated


def process_all_topics(topic_details_csv_path: str, api_key: Optional[str] = None) -> Dict[int, str]:
    """
    Main function to process all topics and generate readable names.
    
    Args:
        topic_details_csv_path: Path to topic_details.csv
        api_key: Optional Groq API key
        
    Returns:
        Dictionary mapping topic_id to readable name
    """
    namer = GroqTopicNamer(api_key=api_key)
    return namer.process_topic_details_csv(topic_details_csv_path)


if __name__ == "__main__":
    """Test the topic namer independently."""
    import sys
    
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = "/Users/wbagger/Documents/Semantic-Analysis-of-TBMM-Transcripts/data/data_secret/topic_details.csv"
    
    print(f"Testing Groq Topic Namer with {csv_path}")
    
    mapping = process_all_topics(csv_path)
    
    print(f"\n📊 Generated {len(mapping)} topic names:")
    for topic_id, name in sorted(mapping.items())[:10]:
        print(f"   {topic_id}: {name}")
