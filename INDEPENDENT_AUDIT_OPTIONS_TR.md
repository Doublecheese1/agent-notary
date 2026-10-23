# Bağımsız güvenlik incelemesi seçenekleri

Henüz hiçbir firmaya başvuru gönderilmedi ve hiçbir firma AgentSolis'i denetlemiş sayılmaz. Başvuru yapılırken `release/agentsolis-security-review-package.zip` ve `SECURITY_REVIEW_SCOPE.md` kullanılmalıdır.

## Kısa liste

- [OpenZeppelin Security Audits](https://www.openzeppelin.com/security-audits): Solidity sözleşmeleri için manuel inceleme, otomatik analiz, gerektiğinde fuzz/invariant testleri ve düzeltme sonrası yeniden inceleme sunuyor. [Başvuru formu](https://www.openzeppelin.com/request?id=talk_to_an_expert-incident_readiness_results).
- [Trail of Bits Blockchain Security](https://trailofbits.com/services/blockchain/): sözleşme, off-chain servis, operasyonel rol ve tehdit modelini birlikte ele alıyor; Slither, Echidna ve Medusa araçlarını kullandığını açıklıyor. [İletişim](https://www.trailofbits.com/contact).
- [Spearbit review süreci](https://docs.spearbit.com/spearbook/anatomy-of-a-spearbit-review/form-submission): resmi inceleme talebinde proje, depo, kapsam, bütçe ve zaman planı isteniyor. [Spearbit](https://spearbit.com/).

## Teklifte istenecek kapsam

1. Üç canlı Arbitrum sözleşmesinin ve deployment ayarlarının satır satır incelemesi.
2. Escrow muhasebesi, erişim kontrolü, imza tekrar saldırısı, zaman pencereleri ve fallback paylaşımı için invariant/fuzz testleri.
3. AI değerlendirme servisi, kanıt indirme, üç KMS imzacı ve relayer için uygulama/API güvenlik incelemesi.
4. Critical/High bulguların düzeltme sonrası yeniden kontrolü ve yayımlanabilir nihai rapor.

Teklif seçimi fiyat, başlangıç tarihi, kişi-gün kapsamı, kaç araştırmacı çalışacağı, fix review dahil olup olmadığı ve raporun kamuya açılabilmesi üzerinden yapılmalıdır.

