# AgentSolis bağımsız güvenlik inceleme kapsamı

Bu dosya denetimin kendisi değildir. Bağımsız denetçiye verilecek kapsamı ve beklenen kanıtı tanımlar.

## Zincirdeki kapsam

- Arbitrum One `AgentNotaryValidatorQuorum`: `0x61835c4f99086006dcea599279c728344341717c`
- Arbitrum One `AgentNotaryAIReviewResolver`: `0x3144c448215c3342c5158fdcce555fae6bfecd58`
- Arbitrum One `AgentNotaryMainnetEscrow`: `0x95ed02f55695fa79744c122436f56541c6270b71`
- Native USDC: `0xaf88d065e77c8cc2239327c5edb3a432268e5831`

`release/arbiscan-verification/verification-report.json` yerel derleme, deployment işlemleri ve zincirdeki runtime kodunun eşleştiğini kaydeder.

## Denetçinin yanıtlaması gereken güvenlik soruları

1. Yetkisiz biri yeni fonlamayı açabilir, sözleşmeyi durdurabilir, resolver'ı değiştirebilir veya escrow'dan para çıkarabilir mi?
2. Aynı anlaşma iki kez ödenebilir ya da iade edilebilir mi?
3. Süreler, fallback paylaşımı, itiraz penceresi ve insan incelemesi bütün durum geçişlerinde fonları erişilebilir tutuyor mu?
4. İmzalar domain, chain ID, sözleşme adresi, nonce ve süreye doğru bağlı mı; tekrar saldırısı mümkün mü?
5. Kötü niyetli ERC-20 davranışı, callback/reentrancy, gas tüketimi, integer sınırları veya olay sıralaması muhasebeyi bozabilir mi?
6. AI sonucu hiçbir zaman tek başına para taşıyor mu; 2/3, güven ve kritik bayrak kontrolleri atlanabilir mi?
7. Web/API katmanında SSRF, prompt injection, gizli anahtar sızıntısı, yetki atlama, idempotency ve kayıp relayer cevabı güvenle ele alınıyor mu?

## Bilinen operasyonel bulgu

Üç Safe ve otomatik karar imzacıları bugün aynı üç adres kümesine dayanıyor; C adresi geçici. Bağımsız C imzacısının ayrı seed/cihaz veya kurumsal KMS ile değiştirilmesi ertelenmiştir. Denetçi bunu merkezî operasyon riski olarak değerlendirmelidir.

## Beklenen teslimat

- Bulgular: Critical/High/Medium/Low/Informational
- Her bulgu için etkilenmiş dosya ve satır, uygulanabilir saldırı senaryosu, örnek test ve düzeltme önerisi
- Düzeltmelerden sonra ikinci inceleme ve kapanış kanıtı
- Denetlenen commit SHA, üç sözleşme adresi ve denetim tarihi

Bağımsız rapor ve düzeltme kontrolü tamamlanana kadar `MAINNET_ACCEPTING_FUNDS=false` ve sözleşmede `publicAccess=false` korunur.
