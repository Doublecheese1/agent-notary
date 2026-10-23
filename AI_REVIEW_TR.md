# AgentNotary — AI-öncelikli uyuşmazlık incelemesi

Bu katman, “AI çoğu vakayı incelesin; yalnızca zor vakalar kurucuya gelsin” hedefini uygular. Henüz bir mainnet dağıtımı değildir ve AI/Safe/KMS kimlik bilgileri yapılandırılmadan etkinleşmez.

## İşleyiş

1. Buyer Review anlaşmasında alıcı uyuşmazlık açar.
2. İş şartları, teslimat, alıcı iddiası ve kanıt manifesti değiştirilemez bir inceleme paketine dönüştürülür. SHA-256 paket özeti kaydedilir.
3. Ayrı hesap ve uç nokta kullanan A, B ve C değerlendiricileri aynı paketi bağımsız okur. Kanıtın içindeki metin talimat sayılmaz; yalnızca veri kabul edilir.
4. Aynı yönde en az iki sonuç, en az `%85` güven, sıfır kritik bayrak ve en fazla `250 USDC` tutar varsa sonuç `READY_FOR_SIGNING` olur.
5. Üç izole signer servisinden en az ikisi aynı EIP-712 kararını imzalar. Uygulama sunucusu signer private key'i tutmaz.
6. Karar `AgentNotaryAIReviewResolver` üzerinde beklemeye alınır. Para henüz dağılmaz.
7. Alıcı veya satıcı itiraz süresinde tek işlemle itiraz edebilir. İtiraz varsa otomatik sonuç kesinleşemez.
8. İtiraz yoksa süre sonunda herhangi biri kararı zincirde kesinleştirebilir. İtiraz veya eskalasyon varsa yalnızca Human Review Safe karar verir.

`.github/workflows/ai-review.yml` her 15 dakikada korumalı `/internal/ai-review/sync` uç noktasını çağırır. Senkronizasyon zincirde kesinleşmiş yeni uyuşmazlıkları bulur, yalnız izin verilen herkese açık kanıt alan adlarından sınırlı boyutta içerik alır, üç değerlendirmeyi çalıştırır, iki izole signer imzasını toplar ve işlemi idempotency anahtarı kullanan relayer'a verir. Relayer cevabı kaybolursa otomatik tekrar yapılmaz; vaka kurucu panelinde `RELAY_UNRESOLVED` görünür.

## Doğrudan insan kuyruğuna giden vakalar

- AI değerlendirmeleri 2/3 çoğunluğa ulaşmazsa,
- güven eşiği `%85` altında kalırsa,
- kanıt eksik veya erişilemezse,
- şartlar belirsizse,
- prompt injection ya da güvenlik/hukuk riski işaretlenirse,
- anlaşma otomatik inceleme üst sınırını aşarsa,
- alıcı veya satıcı AI kararına itiraz ederse.

Bu vakalar yalnız gizli adres ve parola ile açılan özel rapor ekranındaki **İnsan müdahalesi bekleyenler** alanında görünür. Günlük 08:00 ve 00:00 raporlarında da listelenir.

## Para güvenliği

- AI sağlayıcı API anahtarları yalnız Render secrets içinde tutulur.
- Cüzdan private key'i, seed phrase veya Safe sahibi anahtarı web uygulamasında tutulmaz.
- Üç AI cevabı doğrudan para taşıyamaz; zincir 2/3 EIP-712 signer imzası ister.
- AI kararı tarafların itiraz süresi dolmadan uygulanmaz.
- Resolver'ın aldığı uyuşmazlık ücretleri permissionless `sweepFees` ile Treasury Safe'e aktarılır.
- Human Review Safe, otomatik yolun dışında kalan vakaları çözer.

## Dağıtım sırası

1. Treasury Safe, Operations Safe ve Human Review Safe kurulur.
2. Üç AI sağlayıcı hesabı ve üç ayrı KMS/HSM signer servisi kurulur.
3. `AgentNotaryAIReviewResolver` dağıtılır: varsayılan cap `250 USDC`, itiraz penceresi `24 saat`, güven eşiği `8500 bps`.
4. Escrow, review resolver olarak bu kontrat verilerek dağıtılır.
5. Operations Safe `bindEscrow` işlemini bir kez yapar.
6. `MAINNET_ACCEPTING_FUNDS=false` iken düşük tutarlı kendi canary senaryoları çalıştırılır: uzlaşma, itiraz, düşük güven, kritik bayrak, yüksek tutar ve human resolution.
7. Bağımsız inceleme ve canary tamamlanmadan dış kullanıcı fonları açılmaz.

## Dışarıdan tamamlanması gereken yapılandırma

Kod tamam olsa da gerçek otomatik çalışma için üç AI hesabının URL/model/API anahtarı, üç bağımsız signer/KMS adresi, Human Review Safe sahipleri, kalıcı veritabanı, izin verilen kanıt ağ geçitleri ve gas ödeyen idempotent bir relayer gerekir. Bunlar üçüncü taraf hesap/kimlik bilgileri olduğu için kaynak paketin içine gömülmez.
