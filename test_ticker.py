import requests
import json

symbol = "PERP_BTC_USDT"
base_url = "https://api.woox.io"

endpoints = [
    f"/v1/public/futures/{symbol}",
    f"/v1/public/info/{symbol}",
    f"/v1/public/token",
    f"/v1/public/market_trades?symbol={symbol}&limit=1"
]

for ep in endpoints:
    try:
        url = base_url + ep
        print(f"Testing {url}")
        resp = requests.get(url)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(json.dumps(resp.json(), indent=2)[:500])
    except Exception as e:
        print(e)
