# AgentNotary ödeme denemesi

Bu paket Arbitrum Sepolia TEST ağı içindir. Gerçek para kazandırmaz; ana ağ sözleşme tarafından reddedilir. Mevcut /play ve /v1 API davranışı korunur. Yeni ekran /payments adresindedir. Henüz halka açık test ağına sözleşme kurulmadı.

## Ne çalışıyor?

Alıcı test USDC için sınırlı harcama izni verir, ardından bütçe + 0.005 test USDC kilitler. Yalnızca belirtilen satıcı teslim edebilir. Önceden belirlenmiş UTF-8 metni birebir teslim ederse satıcı ödenir ve komisyon treasury cüzdanına aynı işlemde gider. Farklı teslimatta bütçe alıcıya, 0.005 treasury cüzdanına gider. Süre dolunca herhangi biri iade işlemini tetikleyebilir: bütçe ve sabit ücret tamamen asıl alıcıya döner. İade kendiliğinden zamanlanmaz.

10 test USDC örneği: 10.005 kilit; başarıda satıcıya 9.85 ve treasury'ye 0.155. Hatalı teslimatta alıcıya 10 ve treasury'ye 0.005. Süre dolarsa alıcıya 10.005. Ağ işlem maliyeti bu rakamlardan ayrıdır.

Yeni sözleşme 6 ondalıklı tam sayılar kullanır; %1.5 komisyon mikro-USDC'ye aşağı yuvarlanır. Eski API'nin 4 ondalıklı float yuvarlaması değiştirilmedi. Çok küçük tutarlarda iki sistem farklı sonuç verebilir. API'de *_units alanlarını 1,000,000'a bölerek test USDC tutarını elde edin.

## Kabul kriterinin sınırı

Bu sürüm yalnızca önceden bilinen metnin hash eşleşmesini doğrular. JSON şeması, araştırma kalitesi veya doğal dil kriterlerini değerlendirmez. Alıcı beklenen içeriği önceden biliyor olmalıdır; genel agent işlerinin kalitesini çözmüş değildir. Teslim edilen metin zincirde herkese açıktır. Gizli veri kullanmayın. Eski basit doğrulama gerçek ödemeye bağlanmadı.

## GitHub ve Render kurulumu

1. ZIP'i açın. İçindekileri mevcut repo köküne yerleştirin; özellikle main.py güncellensin. static/, contracts/, artifacts/ ve scripts/ klasörlerini koruyun. Dosyaları tek düz klasöre dökmeyin. .env veya özel anahtar yüklemeyin.
2. Render'da yeni commit'i deploy edin. Dockerfile ve requirements.txt pakette mevcut. Varsayılan PAYMENTS_ENABLED=false ile /play çalışır ve /payments kurulum ekranı açılır. Render yüklemesi sözleşmeyi otomatik kurmaz.
3. EVM cüzdan eklentili tarayıcıda Arbitrum Sepolia (421614) test ağını seçin. Alıcı ve satıcı için iki ayrı test hesabı hazırlayın. İşlem yapan hesaplara test ETH, alıcıya resmi test USDC gerekir. Gerçek USDT/USDC göndermeyin. Paribu yatırma adresini treasury olarak kullanmayın; kendi kontrolünüzdeki test cüzdanını kullanın.
4. /payments ekranında First-time deployment bölümünü açın. Treasury test cüzdan adresini girin. Cüzdanda sözleşme kurulum işlemini inceleyip onaylayın. Seed veya özel anahtar uygulamaya girilmez.
5. Kurulum sonucundaki sözleşme adresini Render Environment alanına ekleyin:

   PAYMENTS_ENABLED=true
   PAYMENTS_RPC_URL=https://sepolia-rollup.arbitrum.io/rpc
   PAYMENTS_ESCROW_ADDRESS=kurulan_sozlesme_adresi
   PAYMENTS_TREASURY_ADDRESS=kurulumda_kullanilan_treasury

6. Render'ı yeniden deploy edin. /payments/config enabled:true dönmeli. Alıcı hesabıyla satıcı adresi, tutar ve beklenen metni hazırlayın; önce Approve sonra Lock işlemini cüzdanda onaylayın. deal_id'yi saklayın. Satıcı hesabına geçip aynı metni teslim edin. Yeni anlaşmada farklı metinle iade akışını deneyin.
7. Zaman aşımı testinde kısa süre seçin, süre dolduktan sonra Refund işlemini onaylayın. Sonucu cüzdan token bakiyeleri ve zincir işlem kaydıyla karşılaştırın. Belirsiz işlem sonucunda tekrar göndermeden önce cüzdan geçmişindeki hash'i kontrol edin. Sayfayı yenilemek bekleyen işlemi iptal etmez.

Treasury ve token sözleşmede değiştirilemez. Yanlış adresle kurulum yaparsanız yeni sözleşme gerekir. Sunucu özel anahtar saklamaz ve işlem yayınlamaz; imza cüzdandadır. Ödeme kayıtları zincirdedir. İki blok gözlemi kesin Ethereum L1 finalitesi değildir.

## Doğrulama ve yeniden derleme

Python 3.11+: pip install -r requirements-test.txt ardından python -m unittest -v test_payments test_playground.

Solidity yeniden derlemek için Node ortamında npm install ardından npm run compile. Derleyici solc 0.8.30, OpenZeppelin 5.4.0; derlenmiş ABI ve bytecode artifacts/ içinde hazırdır. TestUSDC yalnızca yerel test tokenıdır, resmi token olarak kurulmaz.

17 test yerel EVM'de geçti: gerçek test token bakiye hareketleri, yetki, tekrar ödeme engeli, süre, iade, fee ve eski API uyumu. Bunlar bağımsız güvenlik denetimi veya halka açık test ağı testi değildir. Ana ağ açılmadan önce gerçek iş doğrulaması, bağımsız sözleşme denetimi ve operasyonel izleme ayrıca tamamlanmalıdır.

Resmi test token adresi: https://developers.circle.com/stablecoins/usdc-contract-addresses

Test USDC edinme: https://faucet.circle.com/

Token transfer kütüphanesi: https://docs.openzeppelin.com/contracts/5.x/api/token/erc20
