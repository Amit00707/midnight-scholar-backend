import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        # Test categories
        categories = ["Philosophy", "Science", "History"]
        for cat in categories:
            resp = await client.get(f"http://localhost:8000/api/books/category/{cat}")
            print(f"Category {cat}: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"  Count: {data.get('count')}")
            else:
                print(f"  Error: {resp.text}")

        # Test recommendations
        resp = await client.post(
            "http://localhost:8000/api/books/recommendations",
            json={"interests": ["philosophy", "science"], "limit_per_category": 4}
        )
        print(f"Recommendations: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  Count: {len(resp.json().get('results', []))}")

if __name__ == "__main__":
    asyncio.run(test())
