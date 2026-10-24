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
