# AgentNotary Playground — teslim ve deploy

## Ne değişti?

- `legacy.py`: Gönderilen `main.py` dosyasının birebir kopyası. Eski uç noktalar, validation, fee, CORS ve kasa davranışı korunur.
- `main.py`: Eski uygulamayı yükler ve yeni playground rotalarını ekler. Render başlangıç hedefi yine `main:app`.
- `playground.py`: Eski motoru ayrı bir Python modülü olarak yükler; ayrı DEALS_DB ve PLATFORM_TREASURY kullanır. Ücret veya validation formülünün ikinci bir uygulaması yoktur.
- `static/play.html` ve `static/app.js`: Buyer/Seller ekranları, iki tek-tık senaryosu, ham HTTP kayıtları, sonuçlar ve kopyalanabilir Python örneği.
- `test_playground.py`, `test_frontend.cjs`: Uyumluluk, izolasyon ve hata akışı testleri.
- `README.md`: Gerçek davranışı anlatır; bozuk URL ve reddedilen eski quickstart düzeltilmiştir.

## Yerelde çalıştırma

Python 3.11+ ile proje dizininde:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m unittest -v test_playground
node test_frontend.cjs
uvicorn main:app --host 127.0.0.1 --port 8000
```

Tarayıcı: http://127.0.0.1:8000/play . Node yalnızca frontend birim testi için gereklidir; uygulama için gerekmez.

## Mevcut Render servisine deploy

1. Mevcut GitHub sürümünü bir commit/tag ile sakla. Bellekteki mevcut deal kayıtları ve kasa sayaçları servis yeniden başladığında kaybolur; bu eski uygulamanın mevcut davranışıdır. Bekleyen kayıtlar varsa yeniden başlatmadan önce yönet.
2. Bu paketin içindeki dosyaları depo köküne ekle. Özellikle `legacy.py`, `playground.py` ve `static/` klasörünü `main.py` ile birlikte yükle. Sadece yeni `main.py` dosyasını yükleme.
3. Docker kullanılıyorsa mevcut Dockerfile çalışır: `COPY . .` yeni dosyaları da alır. Dinlenen port 8000'dir. Tek worker/tek instance kullan; bellek deposu çoklu worker/instance arasında paylaşılmaz.
4. Native Python servisi kullanılıyorsa Build Command: `pip install -r requirements.txt`; Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`. Health Check Path: `/health`.
5. Commit'i yayınla. Auto-deploy etkinse Render otomatik başlatır; değilse Manual Deploy → Deploy latest commit.
6. `/health`, `/docs` ve `/play` adreslerini aç. Playground'da iki senaryoyu çalıştır. Aşağıdaki tutarları ve ham response kayıtlarını kontrol et.
7. Demo öncesi ve sonrası `/v1/analytics/treasury` yanıtını karşılaştır: sandbox işlemleri eski kasa sayaçlarını değiştirmemeli. Başka istemciler eski API'yi kullanıyorsa onların işlemleri sayaçları değiştirebilir.

| $1 bütçe | Kilit | Satıcı | Toplam ücret | Alıcı iadesi |
|---|---:|---:|---:|---:|
| APPROVED | 1.005 | 0.985 | 0.020 | 0 |
| REJECTED | 1.005 | 0 | 0.005 | 1.000 |

Geri alma: Render'da önceki commit'i yeniden deploy et. Bellek kayıtları geri gelmez.

## Cold start ve sandbox sınırları

Sayfa yüklendikten sonra sağlık kontrolü yapılır. 3.5 saniyeden uzun isteklerde waking mesajı çıkar, 90 saniyede zaman aşımı ve yeniden deneme açıklaması gösterilir. POST istekleri otomatik tekrarlanmaz; kaybolan yanıt, işlemin sunucuda tamamlanmadığı anlamına gelmez. Yeni deneme yeni deal oluşturur.

`/play` HTML'i aynı Render servisinden sunulduğundan ilk HTML gelmeden sayfa içi loading göstergesi çalışamaz. Tamamen uyuyan servis için 30 saniye garantisi verilmez. Her zaman anında açılan bir vitrin ayrıca statik hosting gerektirir; bu pakette ek hosting yoktur.

Sandbox en fazla 1000 kayıt tutar. 15 dakikadan eski kayıtlar sonraki lock/settle çağrısında temizlenir; limitte HTTP 429 döner. Sandbox'ta işlemler bir kilitle seri hale getirilir. Bu sınırlamalar sadece sandbox'a aittir. Sandbox, eski motorun expires_at alanını döndürür ama kendi 15 dakikalık saklama süresi daha kısadır; otomatik finansal iade veya zamanlayıcı yoktur.

## Doğrulama kapsamı ve bilinen mevcut davranışlar

Bu oturumda daha önce canlı `/openapi.json`, `/` ve `/health` okunmuştur. Gönderilen dosyanın uygulama adı, modelleri, rotaları ve kök yanıtı bu gözlemlerle uyuşuyor. Eski konuşmadaki amount_usdc/validation_rule kodu farklıdır.

Son aşamada canlıya yeniden ağ erişimi başarısız oldu. Canlı lock/settle yanıtları bu çalışmada çalıştırılıp doğrulanmadı; fee ve validation sonuçları gönderilen kaynak üzerinde yerel HTTP testleriyle doğrulandı. Canlı şema eşleşmesi, deploy edilen kodun birebir aynı olduğunu tek başına kanıtlamaz.

Mevcut motor `criteria` metnini kullanmaz. `result` veya `data` kök alanı gerekir; bazı kısa string/boş liste kontrolleri vardır. Python `or` nedeniyle `{"result": []}` veya `{"result": null}` gibi girdiler kabul edilebilir; `{"data": []}` reddedilir. Bu kusurlar eski davranışı korumak için değiştirilmedi. README'deki eski `{status: COMPLETED, records: 50}` teslimatı reddedilir.

Kaynakta blockchain/RPC/USDC transferi, kalıcı DB, gerçek kimlik doğrulama veya timeout'u uygulayan bir görev bulunmaz. `seller_agent_id` eşitliği kimlik doğrulama değildir. `credited_treasury` bir yanıttaki adrestir; zincir üstü ödeme kanıtı değildir. Bu paket söz konusu eksikleri giderdiğini iddia etmez.

## Test sonucu

- Python: 9 test geçti; 40 farklı miktar/payload birleşiminde eski API ve sandbox yanıt eşitliği, OpenAPI uyumluluğu, kasa izolasyonu, 403/404/400/422/429, saklama süresi ve eşzamanlı settlement kontrol edildi.
- Frontend: Yanıttan tutar gösterimi, yalnızca sandbox URL kullanımı, waking ve timeout, bozuk JSON yanıtı, çift tıklama engeli ve POST'un otomatik tekrarlanmaması test edildi.
- Tarayıcı: Gerçek yerel HTTP ile APPROVED ve REJECTED akışları çalıştırıldı.
- Render deploy ve Docker imaj build bu oturumda yapılmadı.

Test ortamı: Python 3.12, FastAPI 0.141.1, Pydantic 2.13.5, httpx 0.28.1, uvicorn 0.52.4. Orijinal requirements alt sürüm sınırları korunmuştur; Render'ın çözdüğü sürümleri deploy sırasında kaydet.
