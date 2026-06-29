import requests
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class ProxyManager:
    def __init__(self, max_proxies=15, timeout=5):
        self.max_proxies = max_proxies
        self.timeout = timeout
        self.working_proxies = []
        self.current_index = 0
    
    def fetch_proxies(self):
        proxies = []
        sources = [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
            "https://free-proxy-list.net/anonymous-proxy.html",
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        ]
        for url in sources:
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    for line in r.text.splitlines():
                        line = line.strip()
                        if ":" in line and not line.startswith("#") and not "html" in line.lower():
                            proxy = line.split()[0] if " " in line else line
                            proxy = proxy.replace("\r", "").replace("\n", "").strip()
                            if ":" in proxy and proxy.split(":")[1].isdigit():
                                proxies.append(f"http://{proxy}")
            except:
                continue
        unique = list(set(proxies))
        random.shuffle(unique)
        return unique[:self.max_proxies * 2]
    
    def validate_proxy(self, proxy_url):
        try:
            proxies = {'http': proxy_url, 'https': proxy_url}
            r = requests.head("http://www.google.com", proxies=proxies, timeout=self.timeout)
            return r.status_code == 200
        except:
            return False
    
    def get_working_proxies(self, limit=5):
        print("   🌐 Fetching free proxies...")
        raw = self.fetch_proxies()
        if not raw:
            print("   ⚠️ No proxies fetched. Fallback to no-proxy.")
            return [None]
        print(f"   🔍 Validating {len(raw)} proxies...")
        working = []
        with ThreadPoolExecutor(max_workers=10) as ex:
            futures = {ex.submit(self.validate_proxy, p): p for p in raw[:self.max_proxies]}
            for f in as_completed(futures):
                p = futures[f]
                if f.result():
                    working.append(p)
                    print(f"      ✅ Working: {p}")
                else:
                    print(f"      ❌ Dead: {p}")
                if len(working) >= limit:
                    break
        if not working:
            print("   ⚠️ No working proxies. Fallback to no-proxy.")
            return [None]
        self.working_proxies = working
        self.current_index = 0
        return working