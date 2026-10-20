# AgentNotary Pilot UX V2

## Sonuç

Mevcut pilot güvenli işlem hazırlama temeline sahip, ancak kullanıcıdan protokolün state machine yapısını bilmesini bekliyor. Buyer, Seller, Arbitrator ve Founder işlemleri aynı sayfada; genel action menüsü, ham JSON, saniye ve basis-point alanları ilk kullanımı gereksiz biçimde zorlaştırıyor.

## Korunacak güvenlik özellikleri

- Arbitrum Sepolia ağ kontrolü
- İşlem öncesi `eth_call` simülasyonu
- Tam tutar için USDC approval
- Hesap veya ağ değişince hazırlanmış işlemi iptal etme
- Transaction hash alındıktan sonra tekrar göndermeyi engelleme
- MetaMask imzasının daima kullanıcıda kalması

## Yeni bilgi mimarisi

### 1. Başlangıç ekranı

Üç seçenek gösterilir:

1. `Create a deal — I am the buyer`
2. `Open an existing deal — Seller / Arbitrator / Buyer`
3. `Try without a wallet — Wallet-free demo`

Founder araçları `/pilot/admin` sayfasına taşınır.

### 2. Hazırlık kontrolü

Kalıcı üst kart:

- MetaMask: connected / çözüm düğmesi
- Wallet: kısa adres ve `Change account`
- Role: Buyer, Seller, Arbitrator veya Not a party
- Network: Arbitrum Sepolia / `Switch network`
- Test ETH: bakiye / `Funding guide`
- Test USDC: bakiye
- Pilot membership: admitted / `Apply`

Eksik bir koşul varsa zincir işlemi düğmesi kapalı olur ve yalnız ilgili çözüm sunulur.

### 3. Buyer wizard

1. Parties
2. Terms and acceptance criteria
3. Amount and deadlines
4. Fallback split
5. Human-readable review

Saniye yerine `1 day — ends Sep 15, 14:30`; basis point yerine `Seller 50% / Buyer 50%` gösterilir. Teknik değerler `Advanced details` altında kalır.

### 4. İki aşamalı funding

- `1/2 Approve exactly 1.00 test USDC`
- `2/2 Lock 1.00 test USDC`

Birinci işlem zincirde doğrulanmadan ikinci düğme açılmaz. Approval'ın para göndermediği açıkça yazılır.

### 5. Deal Workspace

Ham action menüsü kaldırılır. Bağlı cüzdan ve kontrat durumundan rol otomatik bulunur. Kullanıcı yalnız o anda yapabileceği işlemi görür.

Zaman çizgisi:

`Proposed → Funded → Parties accepted → Delivered → Accepted / Disputed → Closed`

Kartta şunlar görünür:

- `You are: Seller`
- Şu anda kimden işlem beklendiği
- Kalan süre
- Tutar ve ücret
- Salt okunur koşullar
- Sıradaki tek ana düğme

Yanlış hesap bağlıysa: `This action requires Seller wallet 0x… — Switch account`.

### 6. Koşulların paylaşılması

Seller ve Arbitrator exact terms metnini elle yeniden yazmaz. Buyer bir paylaşılabilir deal bağlantısı üretir. Bağlantı açıldığında koşullar salt okunur gösterilir ve hesaplanan hash'in zincirdeki `termsHash` ile eşleştiği görünür.

Kontrat yalnız hash sakladığı için okunur koşullar ya kalıcı bir off-chain metadata deposunda ya da hash'i doğrulanan imzalı paylaşım paketinde tutulmalıdır.

### 7. İşlem inceleme ve durum

Review alanı sayfanın altında gizlenmez; tıklanan düğmenin yanında modal veya drawer açılır.

Durumlar:

- Preparing
- Waiting for wallet
- Submitted
- Confirming on Arbitrum Sepolia
- Confirmed
- Failed / Cancelled / Needs attention

Başarılı sonuçta tx hash, explorer bağlantısı, yeni deal state'i ve USDC etkisi tek makbuz kartında gösterilir. Ham calldata yalnız `Advanced details` altında bulunur.

## Öncelik

### P0 — Halka açık pilot öncesi

1. Role/account bar ve yalnız geçerli eylem
2. Readiness checklist
3. Funding için 1/2 ve 2/2 kalıcı ilerleme
4. Inline review ve insan dilinde hata kurtarma
5. Founder araçlarını `/pilot/admin` sayfasına taşıma

### P1

1. Buyer wizard
2. Paylaşılabilir `/pilot/deal/<id>` bağlantısı
3. Canonical terms görüntüleme ve hash doğrulama
4. Timeline ve explorer bağlantılı receipt
5. Deal URI ve dispute evidence görünümü

### P2

1. `My deals` listesi
2. Deadline geri sayımı
3. Mobil WalletConnect
4. Testnet gas sponsorship değerlendirmesi

## Karşılaştırılan resmi örnekler

- Safe transaction checks: https://help.safe.global/articles/2485383995-how-to-perform-basic-transactions-checks-on-safewallet
- Request Finance token approval: https://help.request.finance/en/articles/8622249-what-is-the-token-approval-step-for
- MetaMask network switching: https://support.metamask.io/configure/networks/how-to-change-networks
- WalletConnect UX practices: https://docs.walletconnect.network/wallet-sdk/ios/best-practices
- Escrow.com transaction status: https://www.escrow.com/support/faqs/how-do-i-check-the-status-of-my-transactions
- Kleros Escrow tutorial: https://docs.kleros.io/products/escrow/new-in-progress-kleros-escrow-tutorial
- Circle gas station: https://developers.circle.com/wallets/gas-station/policy-management
- Stripe Payment Links: https://docs.stripe.com/payment-links
