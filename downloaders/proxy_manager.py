import requests
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class ProxyManager:
    def __init__(self, max_proxies=20, timeout=5):
        self.max_proxies = max_proxies
        self.timeout = timeout
        self.working_proxies = []
        self.current_index = 0
    
    def fetch_proxies(self):
        """
        Fetch fresh HTTP/HTTPS proxies from multiple free sources.
        Returns list of proxy URLs (format: http://ip:port).
        """
        proxies = []
        sources = [
            # ProxyScrape API (fast)
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
            # Free Proxy List (plain text)
            "https://free-proxy-list.net/anonymous-proxy.html",
            # OpenProxy (raw)
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
            # Geonode
            "https://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps",
        ]
        
        for url in sources:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    # Parse lines
                    for line in response.text.splitlines():
                        line = line.strip()
                        # Simple IP:PORT format check
                        if ":" in line and not line.startswith("#") and not "html" in line.lower():
                            proxy = line.split()[0] if " " in line else line
                            proxy = proxy.replace("\r", "").replace("\n", "").strip()
                            # Ensure it's IP:PORT format
                            if ":" in proxy:
                                parts = proxy.split(":")
                                if len(parts) >= 2 and parts[1].isdigit():
                                    proxies.append(f"http://{proxy}")
            except Exception:
                continue
        
        # Remove duplicates and shuffle
        unique = list(set(proxies))
        random.shuffle(unique)
        return unique[:self.max_proxies * 2]  # Fetch more, we'll validate later
    
    def validate_proxy(self, proxy_url):
        """Test a single proxy with a HEAD request."""
        try:
            proxies = {'http': proxy_url, 'https': proxy_url}
            response = requests.head("http://www.google.com", proxies=proxies, timeout=self.timeout)
            return response.status_code == 200
        except:
            return False
    
    def get_working_proxies(self, limit=10):
        """
        Fetch and validate proxies, returning a list of working ones.
        """
        print("   🌐 Fetching free proxies...")
        raw_proxies = self.fetch_proxies()
        if not raw_proxies:
            print("   ⚠️ No proxies fetched. Falling back to no-proxy.")
            return [None]  # fallback
        
        print(f"   🔍 Validating {len(raw_proxies)} proxies (this may take a moment)...")
        working = []
        # Use ThreadPoolExecutor for faster validation
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_proxy = {executor.submit(self.validate_proxy, p): p for p in raw_proxies[:self.max_proxies * 2]}
            for future in as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                if future.result():
                    working.append(proxy)
                    print(f"      ✅ Working: {proxy}")
                else:
                    print(f"      ❌ Dead: {proxy}")
                if len(working) >= limit:
                    break
        
        if not working:
            print("   ⚠️ No working proxies found. Falling back to no-proxy.")
            return [None]
        
        self.working_proxies = working
        self.current_index = 0
        return working
    
    def get_next_proxy(self):
        """Get the next proxy in rotation (round-robin)."""
        if not self.working_proxies:
            return None
        proxy = self.working_proxies[self.current_index % len(self.working_proxies)]
        self.current_index += 1
        return proxy