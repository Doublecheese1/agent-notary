# AgentNotary ajan keşfi ve entegrasyon yol haritası

Tarih: 21 Ekim 2026

Bu belge, `research/AgentNotary-CHATGPT-BRIEF-2026-10-21.md` içindeki pazar önerilerini mevcut kaynak kod ve resmî protokol belgeleriyle karşılaştırır. Araştırma belgesi bir öneri girdisidir; buradaki güvenlik ve yayın kapıları uygulanacak karardır.

## Bugün gerçekten mevcut olanlar

- Cüzdan ve kayıt gerektirmeyen `/play` demosu vardır. Gerçek para taşımaz ve ayrı, geçici sandbox durumuyla çalışır.
- FastAPI OpenAPI belgesi ve çalışan REST uçları vardır.
- Mainnet adayı Arbitrum One ve native USDC için hazırlanmıştır; kaynak kod, artifact ve politika hash'leri release manifestinde sabittir.
- Mutasyon hazırlama akışında kayıp cüzdan cevabı, işlem makbuzu kontrolü ve tekrar gönderme engelleri vardır.
- Python istemcide `operation_id` yeniden bağlama ve çift gönderme koruması vardır.
- AI inceleme tasarımında üç sağlayıcı, 2/3 EIP-712 imza ve idempotent relayer sınırı vardır.
- Gerçek para kabulü kapalıdır. Mainnet kontrat adresleri, Safe adresleri, validator/signer servisleri ve bağımsız inceleme tamamlanmamıştır.

## Henüz mevcut olmayanlar

- x402 uyumlu ücretli uç ve Coinbase facilitator doğrulama/settlement entegrasyonu
- Yayımlanmış yerel paket ve uzaktan Streamable HTTP MCP sunucusu
- Çalışan A2A JSON-RPC servisi ve onu doğru biçimde tanımlayan Agent Card
- Protokoller arası doğrulanabilen, yayımlanmış Settlement Attestation Receipt standardı
- MCP Registry, Bazaar, x402scan veya ERC-8004 kaydı
- Herkese açık API anahtarı/faturalama ürünü

## Ürün kararı

AgentNotary'nin ana vaadi yalnız “escrow” değildir:

> Agent-to-agent jobs için deterministik settlement, güvenli tekrar ve doğrulanabilir sonuç kaydı.

x402, MCP ve A2A ana escrow sözleşmesinin yerine geçmez. Bunlar AgentNotary'yi ajanların bulmasını ve çağırmasını sağlayan giriş katmanlarıdır. x402 ile alınan küçük API ücreti, escrow'a yatırılan iş bedelinden ayrı tutulmalıdır.

## Uygulama sırası

### Kapı 1 — Mevcut mainnet adayını güvenli biçimde tamamla

1. Treasury, Operations ve Human Review için gerçek Safe adreslerini oluştur ve threshold değerlerini doğrula.
2. Üç validator/signer adresini ve AI sağlayıcılarını yapılandır.
3. Kontratları deploy edip Arbiscan'de kaynak kodu doğrula.
4. `MAINNET_ENABLED=true`, `MAINNET_ACCEPTING_FUNDS=false` durumunda yalnız kurucu cüzdanlarıyla küçük canary çalıştır.
5. Olaylar, bakiyeler ve rapor toplamları eşleşmeden dış para kabul etme.

Bitiş ölçütü: doğrulanmış kontrat adresleri release manifestinde kayıtlı, canary makbuzları saklı ve yeni para kabul kapısı hâlâ kapalı.

### Kapı 2 — Doğrulanabilir receipt standardı

1. Receipt şemasını sürümlendir: zincir, kontrat, deal ID, operation ID, önceki/yeni durum, tx hash, blok, taraflar, tutar, politika hash'i ve sonuç.
2. Receipt üretimini yalnız kesinleşmiş zincir makbuzundan sonra yap.
3. `GET /v1/receipts/{id}` ve `POST /v1/receipts/verify` ekle.
4. Aynı `operation_id` için aynı sonucu döndür; yeni ödeme veya zincir işlemi üretme.
5. Test vektörlerini ve doğrulama yöntemini açık dokümana ekle.

Bitiş ölçütü: geçerli, değiştirilmiş, yanlış zincir ve tekrar gönderilmiş receipt testleri geçiyor.

### Kapı 3 — MCP sunucusu

İlk sürüm salt okunur ve güvenli araçlarla başlar:

- `get_deal`
- `get_receipt`
- `verify_receipt`
- `get_protocol_status`

Para hareketi hazırlayan araçlar ancak açık yetkilendirme, harcama limiti ve idempotency zorunluluğuyla eklenir:

- `create_escrow`
- `release_escrow`
- `refund_escrow`
- `open_dispute`

Yerel paket ve uzaktan Streamable HTTP aynı şemaları kullanır. Testnet/sandbox varsayılandır. Sunucu veya örnek kod hiçbir private key istemez.

Bitiş ölçütü: resmi MCP doğrulaması, tekrar çağrı testleri ve üç satırlık kurulum örneği geçiyor.

### Kapı 4 — A2A

1. Gerçek bir A2A JSON-RPC uç noktası oluştur.
2. `/.well-known/agent-card.json` yalnız gerçekten çalışan yetenekleri ilan etsin.
3. Kartta sır, iç servis adresi veya doğrulanmamış ödeme iddiası bulunmasın.
4. Escrow durum sorgulama ve receipt doğrulamayı ilk A2A yetenekleri yap.

Bitiş ölçütü: harici bir A2A istemcisi kartı okuyup ilan edilen bir yeteneği başarıyla çağırıyor.

### Kapı 5 — x402 keşfi

1. İlk ücretli kaynak olarak para hareket ettirmeyen `verify_receipt` kullan.
2. Önce Base Sepolia ve çok küçük test fiyatıyla facilitator verify/settle akışını uçtan uca doğrula.
3. x402 v2 yanıtına Bazaar input/output şeması ekle.
4. Ödeme cevabı kaybolduğunda aynı istek kimliğiyle sonuç sorgula; yeniden ücret çıkarma.
5. Ayrı bir harcama limiti ve anomali durdurma katmanı ekle.
6. Ancak ölçülen test ve açık fiyat sayfasından sonra mainnet fiyatını aç.

Bitiş ölçütü: ücretsiz istek 402 döndürüyor, geçerli ödeme tam bir kez settle oluyor, aynı idempotency anahtarının tekrarı ikinci kez ücretlenmiyor ve kaynak Bazaar aramasında görülüyor.

## Pazarlama botunun kullanabileceği doğrulanmış konum

- “Deterministic settlement for agent-to-agent jobs.”
- “Safe retries: an unresolved transaction is checked before another write is prepared.”
- “Verifiable deal state and policy-bound EIP-712 decisions.”

Henüz kullanılmayacak ifadeler: “audited”, “fully autonomous”, “zero risk”, “listed on Bazaar/MCP Registry”, “mainnet live” veya “real-money escrow available”. Bunlar yalnız ilgili bitiş ölçütü kanıtlandıktan sonra kullanılabilir.

## Resmî kaynaklar

- Coinbase x402 Bazaar: https://docs.cdp.coinbase.com/api-reference/v2/rest-api/x402-facilitator/search-resources
- Coinbase Bazaar MCP: https://docs.cdp.coinbase.com/api-reference/v2/rest-api/x402-facilitator/bazaar-mcp-server
- MCP Registry: https://registry.modelcontextprotocol.io/docs
- A2A Agent Card: https://a2a-protocol.org/latest/topics/agent-discovery/

