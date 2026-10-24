# AgentSolis satış ve outreach CRM operasyon standardı

Sürüm tarihi: 24/10/2026  
Ana gönderici: `agentsolis@solists.com.tr`  
Zorunlu CC: `agentsolis@solists.com.tr`

## Amaç

Bu klasör; Grok, Codex ve diğer araştırma ajanlarının bulduğu adayları, yapılan temasları, müşteri cevaplarını, takip mesajlarını ve gerçek AgentSolis dönüşümlerini aynı kayıt düzeninde tutar. Bir kayıt ancak doğrulanmış kaynağa dayanıyorsa kesin bilgi olarak raporlanır.

## Dosyalar

- `crm-leads.csv`: Her kişi veya şirket için tek ana kayıt.
- `crm-interactions.csv`: Gönderilen veya alınan her mesaj için ayrı satır.
- `crm-conversions.csv`: Demo, Founding 50, cüzdan bağlantısı ve zincir üstü escrow dönüşümleri.
- `CRM-YONETICI-RAPORU-SABLONU.md`: Günlük, haftalık ve aylık yönetici raporu.
- `CRM-ALAN-SOZLUGU.md`: Alanların tanımı ve izin verilen değerler.

CSV dosyaları UTF-8 ve virgülle ayrılmış olarak tutulur. Serbest metinde virgül varsa alan çift tırnak içine alınır. Aynı lead için yeni satır açılmaz; `lead_id` korunarak ana kayıt güncellenir. Her etkileşim ve dönüşüm kendi dosyasına yeni satır olarak eklenir.

## İş akışı

1. **Araştır:** Adayın gerçek ve güncel ihtiyacını resmî site, güncel ilan veya kamuya açık profesyonel profil üzerinden bul.
2. **Doğrula:** Şirket, kişi, kaynak, iletişim kanalı ve iletişim adresini ayrı ayrı doğrula. Tahminî e-posta kullanma.
3. **Kaydet:** `crm-leads.csv` içinde benzersiz `lead_id` oluştur. Önerilen biçim: `L-YYYYMMDD-###`.
4. **Hazırla:** Mesajı adayın ihtiyacına göre kişiselleştir. Gönderici ve CC her zaman `agentsolis@solists.com.tr` olsun.
5. **Gönder:** Gerçek gönderim tamamlanmadan `status=sent` yazma. Taslaklar `draft`, gönderime hazır mesajlar `ready` kalır.
6. **Etkileşimi kaydet:** Gerçek gönderimden sonra `crm-interactions.csv` dosyasına `direction=outbound`, `event_type=sent` satırı ekle; `sent_at` ve kullanılan kanıtı yaz.
7. **Cevabı işle:** Müşterinin cevabını anlamını bozmadan kısa özetle. Tam metni CRM'e kopyalamak zorunlu değildir; hassas veri ekleme.
8. **Takip et:** Cevap yoksa ilk gönderimden 4-5 gün sonra en fazla bir takip mesajı gönder. İkinci takip yoktur.
9. **Durdur:** Opt-out, ret, hard bounce veya spam uyarısından sonra iletişimi durdur; `do_not_contact=true` yap ve sebebi kaydet.
10. **Dönüşümü doğrula:** Demo, Founding 50, cüzdan veya escrow olaylarını ancak doğrulanmış ürün/analytics/zincir verisiyle kaydet.

## Lead durumları

- `researched`: Aday bulundu, iletişim kanalı henüz doğrulanmadı.
- `verified`: İhtiyaç, kaynak ve kanal doğrulandı.
- `draft`: Kişiselleştirilmiş mesaj taslağı hazır.
- `ready`: Mesaj gönderime hazır, henüz gönderilmedi.
- `sent`: Mesaj gerçekten gönderildi.
- `replied`: Cevap alındı.
- `qualified`: İhtiyaç ve sonraki adım doğrulandı.
- `demo`: Demo açıldığı doğrulandı.
- `founding50`: Founding 50 başvurusu doğrulandı.
- `wallet_connected`: Cüzdan bağlantısı doğrulandı.
- `escrow_created`: Escrow oluşturulduğu zincirden doğrulandı.
- `escrow_funded`: Escrow fonlandığı zincirden doğrulandı.
- `won`: Ücret doğuran müşteri sonucu kesinleşti.
- `lost`: Fırsat kapandı.
- `do_not_contact`: İletişim kesin olarak durduruldu.

Durumlar bir önceki aşamanın gerçekleştiğini otomatik olarak kanıtlamaz. Örneğin bir escrow cüzdanı e-posta adresiyle doğrulanmış biçimde eşleşmiyorsa, zincir üstü olay ayrı bir dönüşüm olarak tutulur ve müşteriye atfedilmez.

## Cevap sınıflandırması

`reply_class` için izin verilen değerler:

- `positive`: Görüşme, demo, başvuru veya kullanım ilgisi açıkça ifade edildi.
- `question`: Bilgi veya açıklama istedi; ilgi düzeyi henüz kesin değil.
- `neutral`: Alındı benzeri cevap var, sonraki adım yok.
- `not_now`: Şu an uygun olmadığını belirtti.
- `rejected`: Açıkça istemedi veya uygun olmadığını söyledi.
- `opt_out`: Bir daha iletişim kurulmasını istemedi.
- `unknown`: Anlamı güvenle sınıflandırılamadı.

Otomatik duygu analizi yalnız yardımcı etiket olabilir. Müşterinin gerçek sözlerinin yerine geçmez ve kesin bilgi gibi raporlanmaz.

## Follow-up kuralı

- İlk mesajdan **4 veya 5 takvim günü** sonra, cevap yoksa bir kez gönderilir.
- Cevap geldiyse otomatik follow-up durur ve insan/ajan cevabın içeriğine göre yeni görev belirler.
- `hard_bounce`, `spam_warning`, `rejected` veya `opt_out` varsa hiçbir takip gönderilmez.
- Soft bounce varsa adres tekrar doğrulanmadan gönderim yapılmaz.
- Follow-up, ilk mesajın kısa devamı olmalı; yeni uzun tanıtım metni olmamalıdır.
- Her gönderide `CC: agentsolis@solists.com.tr` zorunludur.

## Doğrulanmış veri kuralları

- Ülke yalnız resmî şirket profili, açık müşteri profili, fatura/KYC/CRM kaydı veya güvenilir iş kaynağı ile kaydedilir. IP, dil, isim veya cüzdandan ülke tahmini yapılmaz.
- Cüzdan sahibi, e-posta sahibi veya şirket ilişkisi doğrulanmadan birbirine bağlanmaz.
- `wallet_connected`, `escrow_created`, `escrow_funded`, hacim ve protokol geliri yalnız ürün günlüğü veya zincir üstü kayıtla doğrulanır.
- E-posta teslim edildi sayısı, SMTP/posta sağlayıcısının teslim kaydı varsa yazılır. `sent`, `delivered` anlamına gelmez.
- Açılma ve tıklama verileri yalnız izinli ve çalışan analytics varsa raporlanır; yoksa `unknown` kalır.
- Müşteri cevabı kısa ve tarafsız özetlenir; anlamı değiştirilmez.

## Yönetici metrikleri

Her dönem için aşağıdaki değerler verilir:

1. Araştırılan lead
2. Doğrulanmış lead
3. Hazır mesaj
4. Gönderilen mesaj
5. Teslim edilen mesaj
6. Hard/soft bounce
7. Toplam cevap
8. Olumlu cevap
9. Demo dönüşümü
10. Founding 50 başvurusu
11. Cüzdan bağlantısı
12. Oluşturulan escrow
13. Fonlanan escrow
14. Fonlanan escrow hacmi (USDC)
15. Kesinleşmiş AgentSolis protokol geliri (USDC)

Rapor dönemleri: bugün, dün, bu hafta, son 7 gün, son 21 gün, bu ay, önceki ay, yılbaşından bugüne ve tüm zamanlar. Her başlığın yanında `GG/AA/YYYY` tarih aralığı yazılır.

## Dönüşüm oranları

- Doğrulama oranı = doğrulanmış lead / araştırılan lead
- Gönderim oranı = gönderilen mesaj / doğrulanmış lead
- Teslim oranı = teslim edilen / gönderilen
- Cevap oranı = toplam cevap / teslim edilen
- Olumlu cevap oranı = olumlu cevap / teslim edilen
- Demo oranı = doğrulanmış demo / teslim edilen
- Founding 50 oranı = doğrulanmış Founding 50 / teslim edilen
- Cüzdan bağlantı oranı = doğrulanmış cüzdan bağlantısı / teslim edilen
- Escrow oluşturma oranı = doğrulanmış escrow / teslim edilen
- Fonlama oranı = fonlanan escrow / oluşturulan escrow

Payda sıfırsa oran yerine `veri yok` yazılır. Teslim durumu bilinmiyorsa cevap oranının paydası olarak gönderilen mesaj kullanılabilir; bu durum raporda açıkça belirtilir.

## Segment, ülke ve kanal analizi

Segmentler: `agent_builder`, `sales_automation`, `ai_marketplace`, `developer_tool`, `freelancer`, `small_business`, `integration_partner`, `other`.

Kanallar: `email`, `contact_form`, `linkedin`, `upwork`, `freelancer`, `other_platform`.

Her segment/ülke/kanal için yalnız doğrulanmış kayıtlarla gönderim, cevap, olumlu cevap, demo, escrow ve hacim karşılaştırılır. Ülke bilinmiyorsa `unknown` grubunda kalır; başka ülkeye dağıtılmaz.

## Günlük çalışma kontrolü

- Yeni araştırılan ve doğrulanan adaylar kaydedildi mi?
- Her gönderimin CC kopyası AgentSolis gelen kutusunda görünüyor mu?
- Bounce, spam uyarısı, ret ve opt-out kayıtları işlendi mi?
- Bugün follow-up zamanı gelen adaylardan yalnız uygun olanlara tek takip gönderildi mi?
- Gelen cevaplar kısa ve doğru özetlendi mi?
- Demo, başvuru, cüzdan ve zincir olayları doğrulandı mı?
- Yönetici raporunda tahmin veya atıfsız veri var mı?

## Haftalık müşteri davranışı analizi

Rapor, en iyi ve en zayıf segmentleri; en iyi kanal ve ülkeleri; en çok sorulan soruları; ret sebeplerini; demo ile escrow arasındaki kaybı ve önerilen tek sonraki deneyi içerir. En az 10 teslim edilmiş mesaj veya anlamlı bir dönüşüm olmadan geniş davranış sonucu çıkarılmaz; `örneklem yetersiz` yazılır.

