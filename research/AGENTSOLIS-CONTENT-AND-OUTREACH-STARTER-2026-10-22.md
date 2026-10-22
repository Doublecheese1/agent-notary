# AgentSolis içerik ve doğal bağlantı başlangıç planı

## Bugün eklenen arama içerikleri

1. `/x402-vs-agent-escrow` — anlık API ödemesi ile teslimatlı iş escrow’unu ayırır.
2. `/ai-agent-job-evidence` — görev, kanıt, kabul kriteri, süre ve fallback tanımlama kontrol listesi.

## İlk yayın dalgası

Bu paylaşımlar dış kullanıcı fonu açılmadan önce yalnızca demo, tasarım ve teknik geri bildirim istemelidir. “Mainnet live”, “audited”, “fully autonomous” veya gerçek kullanım kanıtı olmayan büyüklük iddiaları kullanılmamalıdır.

### AutoGen GitHub Discussions — Show and tell

**Başlık:** Designing evidence-based settlement for multi-agent jobs — feedback wanted

**Metin:**

We are building AgentSolis, a non-custodial settlement workflow for agent-to-agent jobs that cannot be paid safely in a single API request. A buyer and seller agree on deliverables, evidence, price and deadlines before USDC is locked. The public interface and wallet-free simulation are open for review; public mainnet deposits remain closed while deployment verification, operating wallets, external review and canary checks are completed.

We would value feedback on one narrow question: which agent jobs can be verified objectively, and which should always require buyer acceptance or escalation? Demo: https://agentsolis.solists.com.tr/play — evidence checklist: https://agentsolis.solists.com.tr/ai-agent-job-evidence

### Arbitrum community — Technical Discussion

**Başlık:** Feedback request: native-USDC settlement lifecycle for delivered AI-agent work

**Metin:**

AgentSolis is being prepared on Arbitrum One for jobs where payment should follow delivery rather than happen per request. The proposed lifecycle is Agree → Lock → Deliver → Settle, with evidence hashes, explicit deadlines and a published dispute path. Deposits are still closed; we are reviewing the interface and operational assumptions before a controlled canary.

We are looking for technical feedback on receipt design, timeout safety and how much on-chain data is useful without exposing private work. Overview: https://agentsolis.solists.com.tr/ai-agent-escrow

### Reddit — technical feedback, after checking each community’s current rules

**Başlık:** I’m testing a USDC escrow flow for AI-agent jobs — what evidence would you trust?

**Metin:**

Instant payment works for an API response, but a multi-day report, dataset or code task needs a different flow. I built a wallet-free simulation where the parties define evidence and deadlines before settlement. Public deposits are closed; this is a request for product feedback, not an investment or token promotion.

What evidence would you require before allowing an agent to release payment: content hashes, schemas, signed receipts, buyer approval, or something else? Demo: https://agentsolis.solists.com.tr/play

## Kanallar ve kapılar

| Kanal | Şimdi | Ön koşul |
|---|---|---|
| GitHub repository and discussions | Teknik belgeler ve açık geri bildirim | Repo açıklaması, README ve marka tutarlı olmalı |
| AutoGen Discussions | Dar teknik soru ve Show and tell | Çalışan demo, dürüst durum metni |
| Arbitrum forum/community | Mimari geri bildirim | Arbitrum One tasarımı, kontrat ve canary planı |
| Reddit AI/agent communities | Kural kontrolünden sonra geri bildirim yazısı | Spam olmayan kişisel açıklama, gerçek demo |
| Hacker News Show HN | Henüz bekle | Hızlı onboarding ve herkesin çalıştırabildiği demo |
| x402 ecosystem | Karşılaştırma yazısı; entegrasyon iddiası yok | x402 entegrasyonu yapılırsa çalışan endpoint ve receipt |
| Product directories | Henüz bekle | Kararlı marka, sosyal görsel, destek ve gerçek ürün durumu |

## Ölçüm

- Her bağlantı için kaynak ve tarih kaydedilir.
- UTM parametreli ayrı bağlantılar kullanılır.
- Ziyaret, demo başlangıcı, tamamlanan demo ve Founding 50 ilgisi ayrı ölçülür.
- Satın alınmış, otomatik veya alakasız backlink kullanılmaz.
