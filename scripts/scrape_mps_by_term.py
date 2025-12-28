"""
Web scraper for Turkish Parliament MP information from vekillerimiz.com

This script scrapes MP data for all parliamentary terms (1-28) including:
- Term number
- MP name
- Party affiliation for that specific term

Output: CSV file with term_num, mp_name, party_name columns
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from typing import List, Dict, Optional, Tuple
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Configuration
BASE_URL = "https://vekillerimiz.com"
OUTPUT_FILE = "../data/mps_by_term.csv"
DELAY_BETWEEN_REQUESTS = 0.1  # seconds, reduced for faster scraping
MAX_RETRIES = 3
MAX_WORKERS = 10  # Number of concurrent threads

# Thread-safe print lock
print_lock = Lock()

# Headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


def get_page_with_retry(url: str, max_retries: int = MAX_RETRIES) -> Optional[BeautifulSoup]:
    """
    Fetch a page with retry logic.
    
    Args:
        url: URL to fetch
        max_retries: Maximum number of retry attempts
        
    Returns:
        BeautifulSoup object or None if failed
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  Attempt {attempt + 1} failed for {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"   ❌ Failed to fetch {url} after {max_retries} attempts")
                return None


def get_term_url(term_num: int) -> str:
    """
    Generate the URL for a specific term's MP listing.
    
    Args:
        term_num: Term number (1-28)
        
    Returns:
        URL string
    """
    return f"{BASE_URL}/tbmm-{term_num}-donem-vekilleri/"


def extract_mp_links_from_term_page(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Extract MP links and names from a term listing page.
    
    Args:
        soup: BeautifulSoup object of the term page
        
    Returns:
        List of dicts with 'name' and 'url' keys
    """
    mp_list = []
    
    # Find all MP links - they appear to be in the content area
    # Looking at the HTML structure, MPs are typically in <a> tags
    links = soup.find_all('a', href=re.compile(r'/vekil/'))
    
    for link in links:
        mp_name = link.get_text(strip=True)
        mp_url = link.get('href')
        
        # Make sure it's a full URL
        if mp_url and not mp_url.startswith('http'):
            mp_url = BASE_URL + mp_url
        
        if mp_name and mp_url:
            mp_list.append({
                'name': mp_name,
                'url': mp_url
            })
    
    return mp_list


def extract_party_for_term(soup: BeautifulSoup, term_num: int) -> Optional[str]:
    """
    Extract party name for a specific term from an MP's page.
    
    The format is typically: "17. Dönem Milliyetçi Demokrasi Partisi İzmir Milletvekili"
    But may appear without spaces: "17. DönemMilliyetçi Demokrasi PartisiİzmirMilletvekili"
    
    Args:
        soup: BeautifulSoup object of the MP page
        term_num: Term number to look for
        
    Returns:
        Party name or None if not found
    """
    # Look for text containing "{term_num}. Dönem"
    term_pattern = f"{term_num}\\. Dönem"
    
    # Find all text elements that might contain party info
    # Cast a wider net - look at ALL elements
    for element in soup.find_all():
        text = element.get_text(strip=True)
        
        if re.search(term_pattern, text):
            # Pattern 1: Handle NO SPACES between Dönem and party name
            # Format: "X. DönemParty NameProvinceMilletvekili"
            match = re.search(
                r'(\d+)\.\s*Dönem([A-ZÇĞİÖŞÜ].+?)([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)Milletvekili',
                text
            )
            if match:
                party_and_more = match.group(2).strip()
                province = match.group(3).strip()
                # Remove the province from the end if it's there
                if party_and_more.endswith(province):
                    party_name = party_and_more[:-len(province)].strip()
                else:
                    party_name = party_and_more
                
                if party_name:
                    return party_name
            
            # Pattern 2: Handle WITH SPACES (standard format)
            # Format: "X. Dönem Party Name Province Milletvekili"
            match = re.search(
                r'(\d+)\.\s*Dönem\s+(.+?)\s+([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)\s+Milletvekili',
                text
            )
            if match:
                party_name = match.group(2).strip()
                return party_name
            
            # Pattern 3: Fallback - extract everything between Dönem and Milletvekili
            # Then remove last word (likely province)
            match = re.search(
                r'(\d+)\.\s*Dönem\s*(.+?)\s*Milletvekili',
                text
            )
            if match:
                full_text = match.group(2).strip()
                # Split by capital letters to separate words that are stuck together
                # Use lookbehind to keep the capital letter with the word
                words = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]*(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]*)*', full_text)
                
                if len(words) > 1:
                    # Last word is likely the province, everything else is party
                    party_name = ' '.join(words[:-1])
                    return party_name
                elif words:
                    return words[0]
    
    return None


def safe_print(message: str):
    """Thread-safe print function."""
    with print_lock:
        print(message)


def scrape_single_mp(mp_info: Dict[str, str], term_num: int, idx: int, total: int) -> Optional[Dict[str, str]]:
    """
    Scrape a single MP's party information.
    
    Args:
        mp_info: Dict with 'name' and 'url'
        term_num: Term number
        idx: Current index
        total: Total number of MPs
        
    Returns:
        Dict with term, mp_name, party or None if failed
    """
    mp_name = mp_info['name']
    mp_url = mp_info['url']
    
    # Fetch MP's individual page
    time.sleep(DELAY_BETWEEN_REQUESTS)  # Be polite
    mp_soup = get_page_with_retry(mp_url)
    
    if not mp_soup:
        safe_print(f"   [{idx}/{total}] ❌ {mp_name} - Failed to fetch")
        return None
    
    # Extract party for this term
    party = extract_party_for_term(mp_soup, term_num)
    
    if party:
        safe_print(f"   [{idx}/{total}] ✅ {mp_name} - {party}")
        return {
            'term': term_num,
            'mp_name': mp_name,
            'party': party
        }
    else:
        safe_print(f"   [{idx}/{total}] ⚠️  {mp_name} - No party found")
        return {
            'term': term_num,
            'mp_name': mp_name,
            'party': ''
        }


def scrape_term(term_num: int, existing_keys: set = None) -> List[Dict[str, str]]:
    """
    Scrape all MPs and their parties for a specific term using concurrent requests.
    
    Args:
        term_num: Term number (1-28)
        existing_keys: Set of (term, mp_name) tuples to skip
        
    Returns:
        List of dicts with 'term', 'mp_name', 'party' keys
    """
    if existing_keys is None:
        existing_keys = set()
    
    print(f"\n📥 Scraping Term {term_num}...")
    
    term_url = get_term_url(term_num)
    soup = get_page_with_retry(term_url)
    
    if not soup:
        print(f"   ❌ Could not fetch term {term_num} page")
        return []
    
    # Extract MP links
    mp_links = extract_mp_links_from_term_page(soup)
    
    # Filter out MPs that already exist
    mp_links_to_scrape = []
    skipped_count = 0
    
    for mp_info in mp_links:
        key = (term_num, mp_info['name'])
        if key in existing_keys:
            skipped_count += 1
        else:
            mp_links_to_scrape.append(mp_info)
    
    if skipped_count > 0:
        print(f"   ⏭️  Skipping {skipped_count} MPs already in CSV")
    
    if not mp_links_to_scrape:
        print(f"   ✅ All {len(mp_links)} MPs already scraped!")
        return []
    
    print(f"   Found {len(mp_links_to_scrape)} new MPs to scrape - processing with {MAX_WORKERS} concurrent workers...")
    
    results = []
    
    # Use ThreadPoolExecutor for concurrent requests
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_mp = {
            executor.submit(scrape_single_mp, mp_info, term_num, idx, len(mp_links_to_scrape)): mp_info
            for idx, mp_info in enumerate(mp_links_to_scrape, 1)
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_mp):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                mp_info = future_to_mp[future]
                safe_print(f"   ❌ Error processing {mp_info['name']}: {e}")
    
    return results


def load_existing_data(output_file: str) -> Tuple[List[Dict[str, str]], set]:
    """
    Load existing CSV data if it exists.
    
    Args:
        output_file: Path to CSV file
        
    Returns:
        Tuple of (list of existing records, set of (term, mp_name) tuples)
    """
    if not os.path.exists(output_file):
        return [], set()
    
    existing_data = []
    existing_keys = set()
    
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_data.append(row)
                # Create unique key from term and mp_name
                key = (int(row['term']), row['mp_name'])
                existing_keys.add(key)
        
        print(f"📂 Loaded {len(existing_data)} existing records from {output_file}")
        return existing_data, existing_keys
    except Exception as e:
        print(f"⚠️  Error loading existing data: {e}")
        return [], set()


def save_to_csv(data: List[Dict[str, str]], output_file: str, append: bool = False):
    """
    Save scraped data to CSV file.
    
    Args:
        data: List of dicts with term, mp_name, party
        output_file: Path to output CSV file
        append: If True, append to existing file; if False, overwrite
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
    
    mode = 'a' if append else 'w'
    write_header = not append or not os.path.exists(output_file)
    
    with open(output_file, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['term', 'mp_name', 'party'])
        if write_header:
            writer.writeheader()
        writer.writerows(data)
    
    action = "Appended" if append else "Saved"
    print(f"💾 {action} {len(data)} records to {output_file}")


def test_single_mp(mp_url: str, term_num: int):
    """
    Test scraping a single MP for debugging.
    
    Args:
        mp_url: Full URL to MP's page
        term_num: Term number to extract party for
    """
    print("=" * 80)
    print("DEBUG MODE: Testing single MP")
    print("=" * 80)
    print(f"URL: {mp_url}")
    print(f"Term: {term_num}")
    print("=" * 80)
    
    soup = get_page_with_retry(mp_url)
    if not soup:
        print("❌ Failed to fetch page")
        return
    
    print("\n🔍 Searching for party information...")
    
    # Find all text that contains the term number
    term_pattern = f"{term_num}\\. Dönem"
    matches = []
    
    for element in soup.find_all():
        text = element.get_text(strip=True)
        if re.search(term_pattern, text):
            matches.append({
                'tag': element.name,
                'text': text[:200]  # First 200 chars
            })
    
    print(f"\nFound {len(matches)} elements containing '{term_num}. Dönem':")
    for i, match in enumerate(matches, 1):
        print(f"\n{i}. Tag: <{match['tag']}>")
        print(f"   Text: {match['text']}")
    
    # Try to extract party
    party = extract_party_for_term(soup, term_num)
    
    print("\n" + "=" * 80)
    if party:
        print(f"✅ Extracted party: {party}")
    else:
        print("❌ Could not extract party")
    print("=" * 80)


def main():
    """Main execution function."""
    import sys
    import argparse
    # Update global settings
    global MAX_WORKERS, DELAY_BETWEEN_REQUESTS
    
    parser = argparse.ArgumentParser(description='Scrape Turkish Parliament MP data')
    parser.add_argument('--test', nargs=2, metavar=('TERM', 'URL'), 
                        help='Test mode: scrape single MP')
    parser.add_argument('--terms', type=str, default='1-28',
                        help='Term range to scrape (e.g., "1-5" or "17" or "1-28")')
    parser.add_argument('--workers', type=int, default=MAX_WORKERS,
                        help=f'Number of concurrent workers (default: {MAX_WORKERS})')
    parser.add_argument('--delay', type=float, default=DELAY_BETWEEN_REQUESTS,
                        help=f'Delay between requests in seconds (default: {DELAY_BETWEEN_REQUESTS})')
    
    args = parser.parse_args()
    
    
    MAX_WORKERS = args.workers
    DELAY_BETWEEN_REQUESTS = args.delay
    
    # Check for test mode
    if args.test:
        try:
            term_num = int(args.test[0])
            mp_url = args.test[1]
            test_single_mp(mp_url, term_num)
            return
        except ValueError:
            print("Error: Term number must be an integer")
            return
    
    # Parse term range
    if '-' in args.terms:
        start_term, end_term = map(int, args.terms.split('-'))
    else:
        start_term = end_term = int(args.terms)
    
    print("=" * 80)
    print("TURKISH PARLIAMENT MP SCRAPER (FAST MODE)")
    print("=" * 80)
    print(f"Source: {BASE_URL}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Terms: {start_term}-{end_term}")
    print(f"Concurrent workers: {MAX_WORKERS}")
    print(f"Delay per request: {DELAY_BETWEEN_REQUESTS}s")
    print(f"Resume mode: Enabled (skips existing MPs)")
    print("=" * 80)
    
    # Load existing data
    existing_data, existing_keys = load_existing_data(OUTPUT_FILE)
    
    start_time = time.time()
    total_new_mps = 0
    
    # Scrape each term
    for term_num in range(start_term, end_term + 1):
        try:
            term_start = time.time()
            term_data = scrape_term(term_num, existing_keys)
            term_duration = time.time() - term_start
            
            if term_data:
                # Save immediately after each term (append mode)
                save_to_csv(term_data, OUTPUT_FILE, append=True)
                
                # Update existing_keys with new entries
                for mp in term_data:
                    key = (int(mp['term']), mp['mp_name'])
                    existing_keys.add(key)
                
                total_new_mps += len(term_data)
                print(f"✅ Term {term_num}: Scraped and saved {len(term_data)} new MPs in {term_duration:.1f}s")
            else:
                print(f"✅ Term {term_num}: No new MPs to scrape (completed in {term_duration:.1f}s)")
            
        except Exception as e:
            print(f"❌ Error scraping term {term_num}: {e}")
            continue
    
    total_duration = time.time() - start_time
    
    # Final summary
    print("\n" + "=" * 80)
    print("✅ SCRAPING COMPLETE!")
    print("=" * 80)
    print(f"📊 New MPs scraped: {total_new_mps}")
    print(f"📊 Total MPs in CSV: {len(existing_keys)}")
    print(f"📊 Terms covered: {start_term}-{end_term}")
    print(f"⏱️  Total time: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"📊 Output file: {OUTPUT_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
