# AgentSolis outreach CRM

Bu kayıt sistemi kurucu rapor ekranının içindedir. Yalnız kamuya açık iş
iletişim bilgilerini, gerçek gönderimleri, cevapları ve takip tarihlerini tutar.
E-posta göndermez; izleme pikseli, cihaz parmak izi veya tahmin edilmiş kişisel
bilgi kullanmaz.

## Üretim ayarı

Render persistent disk üzerinde şu değişken kullanılmalıdır:

```text
OUTREACH_CRM_DB_PATH=/var/data/agentnotary/outreach-crm.sqlite3
```

## Salt-okunur e-posta arşivi

E-posta arşivi yalnız Render Secret değişkenleriyle etkinleştirilir. Parola
GitHub'a veya tarayıcıya yazılmaz; senkronizasyon yalnızca IMAP üzerinden
okur, mesaj göndermez, silmez ve değiştirmez.

```text
OUTREACH_IMAP_HOST=mail.solists.com.tr
OUTREACH_IMAP_PORT=993
OUTREACH_IMAP_USER=agentsolis@solists.com.tr
OUTREACH_IMAP_PASSWORD=<Render Secret>
OUTREACH_IMAP_FOLDERS=INBOX,Sent
```

`POST /internal/reporting/outreach/email-archive/sync` yalnız kurucu oturumu
ile çalıştırılır. Her ileti `Message-ID + mailbox` ile tekilleştirilir; konu,
gönderen/alıcı/CC, tarih-saat, yön, durum ve kısa gövde özeti saklanır. Tam
mesaj gövdesi ve ekler arşive kopyalanmaz. `GET /internal/reporting/outreach/email-archive`
özel panel için kronolojik arşivi döndürür.

Render'da bunu sürekli çalıştırmak için ayrı bir Cron Job oluşturulmalıdır:

```text
Komut: python email_archive_job.py
Zamanlama: */15 * * * *
```

Cron Job aynı özel veritabanı/persistent disk'e erişmelidir. Web servisi yalnız
paneli gösterir; Cron Job her 15 dakikada bir salt-okunur IMAP senkronizasyonu
yapar. Cron kurulmadan panel arşivi yalnız elle çağrılan `/sync` ile güncellenir.

Ücretli Cron kullanılmak istenmezse aynı Web Service içinde arka plan döngüsü
kullanılabilir. Bunun için şu değişkenler eklenir:

```text
OUTREACH_IMAP_BACKGROUND_SYNC=true
OUTREACH_IMAP_SYNC_INTERVAL_SECONDS=86400
```

Bu seçenek ayrı Render hizmeti oluşturmaz; mevcut web servisi açık kaldığı
sürece günde bir kez IMAP senkronizasyonu yapar. Web Service yeniden
başlarsa döngü otomatik yeniden başlar. Servis uykuya geçerse senkron da o
süre boyunca çalışmaz; uyanınca tekrar devam eder.

Mevcut rapor oturumu bütün CRM uçlarını da korur. Uçlar OpenAPI belgesinde
gösterilmez.

## Kayıt akışı

1. Aday, `POST /internal/reporting/outreach/leads` ile `draft` olarak eklenir.
2. Mesaj gerçekten gönderildiğinde
   `POST /internal/reporting/outreach/leads/{id}/events` çağrısında `kind=sent`
   kaydedilir. Bir taslak kendiliğinden gönderilmiş sayılmaz.
3. Cevap geldiğinde `kind=replied` ve cevabın kısa, yorumsuz özeti yazılır.
4. Olumlu cevap, demo, Founding 50, escrow ve satış aşamaları ayrı olaylardır.
5. Takip gerçekten gönderildiğinde `kind=follow_up` kullanılır. `bounced`,
   `opt_out`, `won` ve `lost` durumlarında takip tarihi otomatik kaldırılır.

## Veri kuralları

- Ülke yalnız kaynağı doğrulandıysa `country_verified=true` ile saklanır.
- Cüzdan veya deal ID yalnız müşteriyle bağlantı açıkça doğrulandıysa
  `relationship_verified=true` ile saklanır.
- Özel e-posta tahmini yapılmaz. İletişim adresi, formu veya platform profili
  kamuya açık iş kanalı olmalıdır ve kaynak URL ile birlikte kaydedilir.
- Cevap özeti, müşterinin söylediğini kısa ve gerçeğe sadık biçimde aktarır;
  duygu veya niyet tahmini içermez.

Kurucu paneli; toplam aday, gerçekten mesaj gönderilen aday, cevap ve olumlu
yanıt oranları, durum hunisi, gecikmiş takip listesi, segment sonuçları ve son
görüşme hareketlerini gösterir.
