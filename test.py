import httpx
from datetime import datetime, timedelta

api_key = "nsNLkh0ZpJbvPc0mEopsbcxysVgPMnCd"

# Get current UTC time and subtract 5 minutes
now = datetime.utcnow()
start_time = now - timedelta(minutes=5)

# Format as YYYY-MM-DD for Polygon API (it requires calendar dates)
date_str = start_time.strftime("%Y-%m-%d")

# Set up API call to just fetch today's data (limit 5 results)
url = f"https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/minute/{date_str}/{date_str}"
params = {
    "apiKey": api_key,
    "limit": 5,
    "sort": "desc"
}

response = httpx.get(url, params=params)
data = response.json()

# Format and print last 5 minutes
for row in data.get("results", []):
    row["datetime"] = datetime.fromtimestamp(row["t"] / 1000).strftime("%Y-%m-%d %H:%M:%S")
    print(row)
