# AgentNotary — fonlama öncesi anlaşma sayfası

`/mainnet/negotiate` buyer ve seller'ın USDC kilitlenmeden önce kısıtları konuşmasını ve ortak şartları kesinleştirmesini sağlar.

## Akış

1. Buyer talep, seller adresi, fiyat, süre, teslimat, sınırlamalar ve istenecek kanıtları yazar.
2. Sistem buyer ve seller için ayrı, yüksek entropili özel bağlantılar oluşturur. Bağlantı anahtarı URL fragment'ında taşınır; HTTP erişim kayıtlarına gönderilmez ve tarayıcı oturum belleğine alınarak adres çubuğundan kaldırılır.
3. Taraflar mesajlaşabilir ve yeni bir final-terms revision önerebilir. Mesajlar yalnızca bağlamdır; bağlayıcı şart değildir.
4. Her yeni revision önceki imzaları temizler. Buyer ve seller, aynı revision için aynı kabul metnini kendi cüzdanlarıyla `personal_sign` kullanarak imzalar.
5. Backend imzadan cüzdan adresini çıkarır. Yalnızca başta belirtilen buyer ve seller adresleri kabul edilir.
6. İki imza tamamlanınca durum `AGREED` olur. “Create escrow from agreed terms” nihai canonical JSON'u, seller ve fiyatı ana ağ escrow formuna aktarır. Buyer yine tüm alanları inceler, USDC onayı verir ve fonlamayı kendi cüzdanında imzalar.

## Saklama ve güvenlik

- Cüzdan private key'i veya seed phrase alınmaz.
- Özel bağlantı anahtarlarının yalnızca SHA-256 özetleri veritabanında tutulur.
- Nihai şartların `keccak256` hash'i gösterilir; escrow fonlanınca aynı canonical metin mevcut `manifestHash` alanına bağlanır.
- SQLite dosyası üretimde geçici Render dosya sistemine konulmamalıdır. `NEGOTIATION_DB_PATH` kalıcı Render diskine ayarlanmalıdır. Kalıcı disk hazır değilse `NEGOTIATION_ENABLED=false` kalır.
- Özel bağlantıya erişen kişi imzasız mesaj gönderebilir; ancak nihai şartları buyer/seller adına kabul edemez. Bağlayıcı kabul cüzdan imzası ister.
- Taraflar fonlamadan önce final terms metnini indirip kendi kayıtlarında tutmalıdır. On-chain kontrat metni değil hash'i saklar.

## Açılış ayarları

```text
NEGOTIATION_ENABLED=true
NEGOTIATION_DB_PATH=/var/data/agentnotary/negotiations.db
```

Bu özellik para kabul kapısından bağımsızdır. Görüşme açılabilir ancak `MAINNET_ACCEPTING_FUNDS=false` iken escrow fonlama işlemi hazırlanmaz.
