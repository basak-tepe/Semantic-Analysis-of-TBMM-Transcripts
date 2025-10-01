from playwright.sync_api import sync_playwright
import os
import time

BASE = "https://www.tbmm.gov.tr"

"""Scrape TBMM transcripts using Playwright to handle JavaScript and perform manual CAPTCHA."""

def scrape_with_playwright(donem, yasama_yili, headless=False):
    save_dir = f"tbmm_tutanaklari_html/d{donem}_y{yasama_yili}_htmls"
    os.makedirs(save_dir, exist_ok=True)

    index_url = f"{BASE}/Tutanaklar/DoneminTutanakMetinleri?Donem={donem}&YasamaYili={yasama_yili}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(index_url)
        page.wait_for_load_state("networkidle")

        input(f"👉 d{donem}/y{yasama_yili}: solve the CAPTCHA and press ENTER")

        links = page.query_selector_all("a[href*='Tutanak?Id=']")
        hrefs = [l.get_attribute("href") for l in links]
        print(f"Found {len(hrefs)} viewer links in d{donem}_y{yasama_yili}")

        for idx, href in enumerate(hrefs, start=1):
            filename = f"d{donem}_y{yasama_yili}_{idx}.html"
            filepath = os.path.join(save_dir, filename)
            if os.path.exists(filepath):
                print(f"[{idx}/{len(hrefs)}] Skipping {filename} (already exists)")
                continue

            viewer_url = BASE + href
            print(f"\n[{idx}/{len(hrefs)}] Visiting viewer: {viewer_url}")
            page.goto(viewer_url)
            page.wait_for_load_state("domcontentloaded")

            html_anchor = page.query_selector("a[title*='Html']")
            if not html_anchor:
                print("   ❌ No Html link found on viewer page — skipping")
                continue

            print("   Clicking HTML link...")
            html_anchor.click()
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)

            html_text = page.content()

            filename = f"d{donem}_y{yasama_yili}_{idx}.html"
            filepath = os.path.join(save_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_text)
            print(f"   ✅ Saved -> {filepath}")

            page.go_back()
            page.wait_for_load_state("domcontentloaded")

        browser.close()

if __name__ == "__main__":
        scrape_with_playwright(23, 2, headless=False)
