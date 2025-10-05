from playwright.sync_api import sync_playwright
import os
import time

BASE = "https://www.tbmm.gov.tr"

def scrape_with_playwright(donem, yasama_yili, headless=False, batch_size=10):
    save_dir = f"tbmm_tutanaklari_html/d{donem}_y{yasama_yili}_htmls"
    os.makedirs(save_dir, exist_ok=True)

    index_url = f"{BASE}/Tutanaklar/DoneminTutanakMetinleri?Donem={donem}&YasamaYili={yasama_yili}"

    done = False
    while not done:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto(index_url)
            page.wait_for_load_state("networkidle")

            input(f"👉 d{donem}/y{yasama_yili}: Solve CAPTCHA (if prompted) and press ENTER...")

            # bütün viewer linklerini al
            links = page.query_selector_all("a[href*='Tutanak?Id=']")
            hrefs = [l.get_attribute("href") for l in links]
            total = len(hrefs)
            print(f"Found {total} viewer links in d{donem}_y{yasama_yili}")

            missing = []
            for idx, href in enumerate(hrefs, start=1):
                filename = f"d{donem}_y{yasama_yili}_{idx}.html"
                filepath = os.path.join(save_dir, filename)

                if os.path.exists(filepath):
                    continue  # already downloaded

                missing.append((idx, href))

            print(f"➡️ {len(missing)} files still missing...")

            if not missing:
                print("🎉 All files downloaded!")
                done = True
                browser.close()
                break

            # batch halinde indir
            for bidx, (idx, href) in enumerate(missing, start=1):
                # her batch'te captcha için dur
                if (bidx - 1) % batch_size == 0 and bidx > 1:
                    print(f"\n🔄 Batch limit reached ({batch_size}). Going back to index for CAPTCHA...")
                    page.goto(index_url)
                    page.wait_for_load_state("networkidle")
                    input(f"👉 Solve CAPTCHA again for d{donem}/y{yasama_yili}, then press ENTER...")

                viewer_url = BASE + href
                filename = f"d{donem}_y{yasama_yili}_{idx}.html"
                filepath = os.path.join(save_dir, filename)

                print(f"\n[{idx}/{total}] Visiting viewer: {viewer_url}")
                try:
                    page.goto(viewer_url, timeout=30_000)
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

                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(html_text)
                    print(f"   ✅ Saved -> {filepath}")

                    # geri dön
                    page.go_back()
                    page.wait_for_load_state("domcontentloaded")

                except Exception as e:
                    print(f"   ⚠️ Error on {viewer_url}: {e}")
                    # bir sonraki while turunda tekrar denenecek

            browser.close()
            print("🔁 Loop finished one pass, checking again for missing files...\n")


if __name__ == "__main__":
    # Örnek: sadece 23/4 indir
    scrape_with_playwright(23, 5, headless=False, batch_size=15)
