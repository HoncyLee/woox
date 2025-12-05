import requests
import json

BASE_URL = "https://api.woox.io"
SYMBOL = "PERP_BTC_USDT"

def get_symbol_info():
    try:
        # Try v1 public info
        url = f"{BASE_URL}/v1/public/info/{SYMBOL}"
        print(f"Fetching info from: {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
            # Try generic info endpoint if specific one fails
            url = f"{BASE_URL}/v1/public/info"
            print(f"Fetching info from: {url}")
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                # Filter for our symbol
                rows = data.get('rows', [])
                for row in rows:
                    if row.get('symbol') == SYMBOL:
                        print(json.dumps(row, indent=2))
                        return
                print(f"Symbol {SYMBOL} not found in generic info.")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    get_symbol_info()
