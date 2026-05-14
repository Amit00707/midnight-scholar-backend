import requests
import json

def test_recommendations():
    url = "http://localhost:8000/api/books/recommendations"
    
    # We need a token. I'll try to get one if I can, but I don't have user credentials.
    # Actually, I'll check the search endpoint first which is public in some apps.
    # But recommendations usually require auth.
    
    # Let's try searching for subjects directly to see if Open Library is up.
    search_url = "https://openlibrary.org/search.json?q=subject:Philosophy&limit=1"
    try:
        resp = requests.get(search_url, timeout=10)
        print(f"Open Library Subject Search Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Found {data.get('numFound')} books for subject:Philosophy")
    except Exception as e:
        print(f"Open Library Search Failed: {e}")

    # Let's try a local search endpoint if it exists
    local_search = "http://localhost:8000/api/books/search?q=subject:Philosophy&limit=1"
    try:
        resp = requests.get(local_search, timeout=10)
        print(f"Local Search Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Local Search Success")
        else:
            print(f"Local Search Error: {resp.text}")
    except Exception as e:
        print(f"Local Search Failed: {e}")

if __name__ == "__main__":
    test_recommendations()
