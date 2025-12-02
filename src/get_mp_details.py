import requests
from bs4 import BeautifulSoup
import sys
import re

def search_wikipedia(query, lang="tr"):
    """Searches Wikipedia for the given query and returns the top result."""
    url = f"https://{lang}.wikipedia.org/w/api.php"
    headers = {
        "User-Agent": "MP_Info_Scraper/1.0 (contact@example.com)"
    }
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        try:
            data = response.json()
        except ValueError:
             # If JSON fails, just return None without printing massive HTML content
            return None

        results = data.get("query", {}).get("search", [])
        if results:
            return results[0]  # Return the top result
        return None
    except Exception as e:
        print(f"Error searching Wikipedia: {e}")
        return None

def get_mp_details(mp_name):
    """Fetches and parses the Wikipedia page for the MP."""
    # print(f"🔍 Searching for: {mp_name}")
    result = search_wikipedia(mp_name)
    
    if not result:
        # print("❌ No Wikipedia page found.")
        return None

    page_title = result["title"]
    page_url = f"https://tr.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
    # print(f"✅ Found Page: {page_title} ({page_url})")

    headers = {
        "User-Agent": "MP_Info_Scraper/1.0 (contact@example.com)"
    }

    try:
        response = requests.get(page_url, headers=headers)
        if response.status_code != 200:
            # print("❌ Failed to fetch page content.")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. Extract Party Name from Infobox
        infobox = soup.find("table", {"class": "infobox"})
        party_name = None
        
        if infobox:
            rows = infobox.find_all("tr")
            for row in rows:
                header = row.find("th")
                data = row.find("td")
                if header and data:
                    key = header.get_text(strip=True)
                    value = data.get_text(strip=True)
                    
                    # Clean up value (remove footnotes like [1], [2])
                    value = re.sub(r'\[\d+\]', '', value)
                    
                    # Look for Party keys
                    if any(k in key.lower() for k in ["siyasi partisi", "partisi", "parti"]):
                        party_name = value
                        break  # Found the party, stop searching
        
        # 2. Extract Terms from Categories
        categories = soup.find("div", {"id": "mw-normal-catlinks"})
        terms = []
        
        if categories:
            cat_links = categories.find_all("a")
            for link in cat_links:
                cat_text = link.get_text()
                # Match patterns like "TBMM 24. dönem milletvekilleri"
                match = re.search(r'TBMM (\d+)\. dönem', cat_text, re.IGNORECASE)
                if match:
                    terms.append(int(match.group(1)))
        
        # Sort terms numerically
        terms = sorted(list(set(terms)))

        # Prepare result
        result_data = {
            "name": mp_name,
            "party": party_name,
            "terms": terms
        }
        
        return result_data

    except Exception as e:
        print(f"Error details: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mp_name = " ".join(sys.argv[1:])
        details = get_mp_details(mp_name)
        if details:
            print(f"Party: {details['party']}")
            print(f"Terms: {details['terms']}")
    else:
        name_input = input("Enter MP Name: ")
        details = get_mp_details(name_input)
        if details:
            print(f"Party: {details['party']}")
            print(f"Terms: {details['terms']}")
