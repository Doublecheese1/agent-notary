# AgentNotary — ETH gelmeden önce tamamlananlar ve son açılış

Tarih: 16 Eylül 2026

## Hazır olanlar

- Arbitrum One ve Circle native USDC sabitlenmiş ana ağ kontratı.
- Otomatik kanıt kontrolü ve Buyer Review anlaşmazlık akışları.
- Başarı ödemesinde %1,5 protokol ücreti, 50 USDC tavan, sabit ücret yok.
- İlk 50 kabul edilen buyer cüzdanına ilk fonlanan ana ağ anlaşmasından itibaren 30 gün protokol ücreti muafiyeti.
- Yeni anlaşmaları durdurma; mevcut anlaşmaların iade/sonuç yollarını açık bırakma.
- İşlem, buyer ve kontrat toplam limitleri.
- Sunucuda private key/seed phrase bulunmayan cüzdan akışı.
- Arbitrum One ağ kimliğiyle hazırlanan işlemler ve onay işlemi kesinleşmeden fonlama adımını açmayan arayüz.
- Kaybolan cevap/yenileme durumunda işlem hash'ini tarayıcıda koruyan ve tekrar göndermeden önce sonucu kontrol eden akış.
- İngilizce şartlar/risk bildirimi, gizlilik taslağı ve doğru Founding 50 ana ağ teklifi.
- Sürümlenmiş otomatik ve Buyer Review politika dosyaları.
- Private key almadan EIP-712 imzası üreten ve 2/3 sonucu zincire taşıyan `/mainnet/validator` konsolu.
- Yeni fonlama kapatıldığında mevcut anlaşmaların teslimat, sonuçlandırma ve iade işlemlerini açık tutan backend kapısı.
- Founding 50 kabulü, normal buyer erişimi ve yeni anlaşmaları durdurma işlemlerini Operations Safe için hazırlayan kapalı `/mainnet/operations` ekranı.
- MetaMask cevabı kaybolsa bile işlem kimliği kesinleşmeden ikinci fonlama/dağıtım göndermeyen tarayıcı koruması.
- Resolver değişikliğinde yeni validator quorum veya AI review resolver'ın incelenmiş mevcut uygulamayla aynı runtime kodunu taşımasını zorunlu kılan rotasyon koruması.
- Üç bağımsız AI değerlendirmesini 2/3 ve en az %85 güven eşiğiyle birleştiren; düşük güven, ayrışma, kritik bayrak, yüksek tutar veya taraf itirazında Human Review Safe'e geçen AI-öncelikli uyuşmazlık katmanı.
- AI kararını doğrudan ödeme yerine zincirde 24 saat bekleten ve alıcı/satıcı itirazını otomatik kesinleşmeden önce kabul eden resolver.
- Arbitrum One olaylarını ve bakiyelerini yalnızca okuyarak her gün İstanbul saatiyle 09.00 ve 20.00'de operasyon raporu gönderen, gizli anahtarla korunan raporlama uç noktası ve GitHub zamanlayıcısı. Rapor para taşımaz ve işlem imzalamaz.
- Buyer ve seller'ın fonlama öncesinde özel bağlantılarla konuştuğu, karşı teklif verdiği, aynı nihai revision'ı kendi cüzdanlarıyla imzaladığı ve yalnızca çift imzalı şartları escrow formuna aktardığı `/mainnet/negotiate` akışı. Mesajlar bağlayıcı değildir; çift imzalı revision değiştirilemez.

## ETH alınmadan yapılacak son organizasyon

Bu adresler private key değildir; yalnızca herkese açık cüzdan adresleridir.

Onaylanmış Arbitrum One deployer/gas cüzdanı: `0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD`. Bu adres kullanıcının MetaMask Account 1 hesabıdır ve kurtarma kelimeleri çevrimdışı yedeklenmiştir. Önceki `0x21a7…c26D` adresi BtcTurk yatırma adresi olduğu için deployer ve ödeme yapılandırmasından çıkarılmıştır. Kontrat dağıtımları yalnızca yeni onaylı cüzdandan hazırlanacaktır.

1. `treasurySafe`: protokol ücretini alacak ayrı Safe adresi.
2. `operationsSafe`: yeni buyer kabulü, yeni anlaşmaları durdurma ve gelecekteki resolver değişiklikleri için ayrı Safe adresi.
3. `humanReviewSafe`: yalnızca AI'ın çözemediği veya tarafların itiraz ettiği Buyer Review vakalarını karara bağlayacak ayrı Safe adresi.
4. `validator A/B/C`: objektif otomatik sonuçları 2/3 olarak imzalayacak üç ayrı doğrulayıcı adresi.
5. `AI reviewer A/B/C`: üç bağımsız AI değerlendirmesinin on-chain karar paketini ayrı KMS/HSM servisleriyle imzalayacak üç adres.

Doğrulayıcıların ayrı kişi/kurum, ayrı cihaz ve ayrı seed kullanması gerekir. İki doğrulayıcının anlaşması 2/3 modelinin temel güven varsayımıdır ve katılımcılara açıklanacaktır.

Safe ve kontratların zincirde oluşturulması gas harcadığı için ETH adımıyla birlikte yapılacaktır. Seed phrase veya private key hiçbir dosyaya, Render ayarına ya da destek mesajına yazılmayacaktır.

## ETH geldikten sonra tek açılış sırası

1. Treasury, Operations ve Human Review Safe adreslerini son kez gözden geçir ve gereken Safe'leri Arbitrum One üzerinde oluştur.
2. Üç validator adresiyle `AgentNotaryValidatorQuorum` dağıt.
3. Operations Safe, Human Review Safe, Treasury Safe ve üç AI reviewer signer ile `AgentNotaryAIReviewResolver` dağıt.
4. Native USDC, treasury Safe, operations Safe, validator quorum ve AI review resolver adresleriyle `AgentNotaryMainnetEscrow` dağıt; Operations Safe ile resolver'ın `bindEscrow` işlemini bir kez yap.
5. Kaynak kodu Arbiscan'de doğrula; constructor adreslerini ve sabit ücret/limitleri zincirden karşılaştır.
6. Render'a RPC, kontrat ve Safe adreslerini ekle; önce `MAINNET_ENABLED=true`, `MAINNET_ACCEPTING_FUNDS=false` kullan.
7. Deployment block, güçlü dashboard parolası, oturum sırrı ve owner ödeme adresini Render'a ekle; `/reports` sayfasının Bugün/Hafta/Ay/Yıl/Tüm zamanlar değerlerini okuduğunu doğrula. E-posta da istenirse `REPORT_RECIPIENT=yguler1@gmail.com`, SMTP uygulama parolası ve rapor token'ını Render'a; endpoint URL'si ile aynı token'ı GitHub Actions secrets alanına ekleyip 09.00/20.00 gönderimini bir kez elle doğrula.
8. Görüşme ve AI review veritabanlarını kalıcı diske bağla. Üç ayrı AI sağlayıcı hesabını ve üç izole signer/KMS servisini secrets ile yapılandır; hiçbir cüzdan anahtarını Render uygulamasına yazma.
9. GitHub CI'ın tam derleme ve test paketini yeşil tamamladığını doğrula.
10. `/mainnet/validator` üzerinden iki bağımsız validator imzasıyla 10 USDC Automatic canary anlaşmasını tamamla ve tüm bakiyeleri/olayları kontrol et.
11. Buyer Review canary'de AI 2/3 uzlaşması, taraf itirazı, düşük güven, kritik bayrak, yüksek tutar ve Human Review Safe yollarını ayrı ayrı doğrula.
12. Bağımsız güvenlik incelemesi/audit sonucundaki para güvenliğini etkileyen maddeleri kapat.
13. Kritik fark yoksa `/mainnet/operations` ile ilk buyer cüzdanı için Safe işlemini hazırla ve imzalat. En son `MAINNET_ACCEPTING_FUNDS=true` yap.

## Açılmayı otomatik durduran şartlar

- Kontrat kaynak doğrulaması başarısızsa.
- Token adresi native Circle USDC değilse.
- Uygulamanın okuduğu treasury/operations/resolver adresleri dağıtımdaki adreslerle eşleşmiyorsa.
- Ana ağ işlemi `chainId 42161` dışında hazırlanıyorsa.
- Canary anlaşmasında ödenen/iade edilen toplamlar beklenenle uyuşmuyorsa.
- Resolver politikası ve iletişim/olay müdahale sorumlusu belirlenmemişse.
- Bağımsız güvenlik incelemesi tamamlanmamışsa veya kritik/yüksek bulgu açıksa.

Bu koşullarda `MAINNET_ACCEPTING_FUNDS` kapalı kalır; site bilgi amaçlı çalışır ama fonlama işlemi hazırlamaz.
