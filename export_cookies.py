"""
YouTube Cookies Exporter for Age-Restricted & Member-Only Videos
Extracts session cookies from installed browsers into cookies.txt
"""

import sys
import http.cookiejar
from pathlib import Path
from yt_dlp.cookies import extract_cookies_from_browser, YDLLogger
from yt_dlp import YoutubeDL

OUTPUT_COOKIE_FILE = Path("cookies.txt")


def export_cookies_from_browser(browser_name: str = "edge") -> bool:
    print(f"[*] Attempting to extract YouTube cookies from {browser_name.title()}...")
    try:
        ydl = YoutubeDL({"quiet": True})
        logger = YDLLogger(ydl)
        jar = extract_cookies_from_browser(browser_name, None, logger)
        
        # Filter for youtube/google cookies
        mozilla_jar = http.cookiejar.MozillaCookieJar(str(OUTPUT_COOKIE_FILE))
        count = 0
        for cookie in jar:
            if any(domain in cookie.domain for domain in ["youtube.com", "google.com", ".youtube.com", ".google.com"]):
                mozilla_jar.set_cookie(cookie)
                count += 1

        if count > 0:
            mozilla_jar.save(ignore_discard=True, ignore_expires=True)
            print(f"[+] SUCCESS! Extracted {count} YouTube/Google cookies to: {OUTPUT_COOKIE_FILE.resolve()}")
            return True
        else:
            print(f"[!] Warning: No YouTube cookies found in {browser_name.title()}. Are you signed into YouTube in that browser?")
            return False

    except PermissionError:
        print(f"[!] {browser_name.title()} is currently OPEN and locking its cookie database.")
        print(f"    Please close {browser_name.title()} completely for 5 seconds and run this script again.")
        return False
    except Exception as e:
        print(f"[!] Could not extract from {browser_name}: {e}")
        return False


def main():
    print("=" * 60)
    print("🍪 YOUTUBE COOKIES EXPORTER")
    print("=" * 60)

    # Try installed browsers
    for b in ["edge", "chrome", "firefox", "brave"]:
        if export_cookies_from_browser(b):
            sys.exit(0)

    print("\n" + "-" * 60)
    print("ℹ️ ALTERNATIVE: MANUAL EXPORT (Takes 30 seconds)")
    print("-" * 60)
    print("1. In Chrome or Edge, install the extension: 'Get cookies.txt LOCALLY'")
    print("2. Go to https://www.youtube.com (ensure you are logged in)")
    print("3. Click the extension icon and click 'Export'")
    print(f"4. Save the file as: {OUTPUT_COOKIE_FILE.resolve()}")
    print("-" * 60)


if __name__ == "__main__":
    main()
