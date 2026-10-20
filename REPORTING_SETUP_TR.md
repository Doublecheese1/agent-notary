# AgentNotary — özel rapor sayfası ve isteğe bağlı e-posta

Rapor yalnızca Arbitrum One olaylarını ve bakiyelerini okur. Cüzdan private key'i, seed phrase veya işlem imzalama yetkisi kullanmaz. Özel internet sayfası e-posta hesabı gerektirmez; 09.00 ve 20.00 e-postaları ayrıca istenirse açılır.

## Render gizli ortam ayarları

Kişisel alıcı adresini ve Gmail uygulama parolasını kaynak koda yazmayın. Render Environment bölümüne ekleyin:

```text
REPORTING_ENABLED=true
MAINNET_DEPLOYMENT_BLOCK=<escrow deployment block>
REPORT_TIMEZONE=Europe/Istanbul
REPORT_DASHBOARD_PASSWORD=<at least 12 characters, preferably a long unique password>
REPORT_SESSION_SECRET=<at least 32 random characters>
REPORT_OWNER_PAYOUT_ADDRESS=<your USDC payout wallet>
```

Yalnızca internet sayfası kullanılacaksa yukarıdaki ayarlar yeterlidir. E-posta da kullanılacaksa ayrıca şunları ekleyin:

```text
REPORT_RECIPIENT=yguler1@gmail.com
REPORT_TRIGGER_TOKEN=<long random secret>
REPORT_SMTP_HOST=smtp.gmail.com
REPORT_SMTP_PORT=465
REPORT_SMTP_USER=<sender Gmail address>
REPORT_SMTP_APP_PASSWORD=<Google app password>
```

`REPORT_SMTP_APP_PASSWORD` normal Google şifresi değildir. Google hesabında iki adımlı doğrulama açıldıktan sonra oluşturulan uygulama parolasıdır; sohbete veya GitHub'a yazılmaz.

## İsteğe bağlı e-posta için GitHub Actions secrets

Repository Settings → Secrets and variables → Actions altında:

```text
REPORT_ENDPOINT_URL=https://<render-service-host>
REPORT_TRIGGER_TOKEN=<Render ile aynı random secret>
```

`.github/workflows/daily-report.yml` yalnızca e-posta istenirse kullanılır. Türkiye saatiyle 09:00 ve 20:00'de korumalı endpoint'i çağırır. GitHub zamanlayıcısı birkaç dakika gecikebilir. Endpoint yalnızca doğru gizli başlıkla çalışır; yanlış veya kapalı durumda 404 döner.

Raporu gönderen Gmail hesabı da `yguler1@gmail.com` olacaksa `REPORT_SMTP_USER=yguler1@gmail.com` kullanılır. Uygulama parolası yalnızca Render'ın gizli Environment alanına girilir; kaynak pakete, GitHub dosyalarına veya sohbete eklenmez.

## Rapordaki veriler

- Yeni, kabul edilen, teslim edilen ve kapanan anlaşmalar
- Yeni ve açık uyuşmazlıklar
- Validator karar sayısı
- Dönem işlem hacmi
- Seller ödemeleri, buyer iadeleri, resolver ödemeleri
- Dönem ve toplam AgentNotary protokol ücreti
- Kontratta kilitli USDC ve Treasury Safe USDC bakiyesi

Ana ağ kontratı dağıtılmadan ve `MAINNET_DEPLOYMENT_BLOCK` bilinmeden raporlama açılmaz.

## Özel internet rapor sayfası

`https://<render-service-host>/reports` adresi parola sorar. Doğru parola girildiğinde 12 saat geçerli, `HttpOnly`, `Secure` ve `SameSite=Strict` oturum çerezi oluşturur. Rapor ekranı işlem hazırlamaz, para taşımaz ve cüzdan bağlatmaz.

Ekranda **Bugün**, **Bu hafta**, **Bu ay**, **Bu yıl** ve **Tüm zamanlar** ayrı ayrı gösterilir. Her dönemde toplam anlaşma hacmi, kesinleşen AgentNotary protokol geliri, owner cüzdanına çekilen USDC, anlaşma sayısı, kapanan anlaşmalar ve uyuşmazlıklar bulunur.

“Çekilen” tutar tahmin değildir: Treasury Safe'den `REPORT_OWNER_PAYOUT_ADDRESS` olarak belirlenen cüzdana gerçekleşmiş native USDC transferlerinin toplamıdır. Bu adres ayarlanmadan ekran çekilen tutarı sıfır gösterir ve yapılandırma uyarısı verir. Başka gider cüzdanlarına yapılan transferler kişisel çekim sayılmaz.
