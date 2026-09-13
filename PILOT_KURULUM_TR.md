# Ücretsiz ilk 50 — ödeme ekranı kurulumu

## Bu pakette tamamlanan iş
Yeni `/pilot` ekranı ücretsiz Founding sözleşmesine bağlıdır. `/payments` eski test anlaşmalarını yönetmeye devam eder; `/play` değişmedi. Üyelik ve kalan kontenjan yalnızca yapılandırılmış sözleşmeden okunur. Sözleşme yoksa bilinmiyor gösterilir, 50 boş yer varmış gibi gösterilmez.

Ekranda: MetaMask bağlantısı ve test bakiye kontrolü; sözleşme dağıtım hazırlığı; kurucunun ilk 50 alıcı cüzdanını kabul etmesi; teklif/USDC izni/bütçe kilitleme; satıcı ve hakem kabulü; teslimat; alıcı kabulü/itirazı; hakem kararı; üç süre aşımı yolu ve makbuz kontrolü bulunur. Her işlem önce incelenir, sonra cüzdanda onaylanır. Sunucu private key tutmaz ve işlem göndermez.

## Render'a yükleme
1. Paket içeriğini mevcut deponun köküne, alt klasörleri koruyarak aktarın. `static` ve `artifacts` dosyalarını kök klasöre dağıtmayın. Gizli `.env` veya private key yüklemeyin.
2. Render dağıtımı tamamlandıktan sonra `https://agent-notary-5.onrender.com/pilot` açın. `PILOT_ENABLED` henüz tanımlı değilse ekran açılır, ödeme işlemleri yapılandırılmamış görünür.
3. Chrome'da MetaMask'i bağlayın. Mevcut 20 test USDC iş bedeli içindir; dağıtım ve işlem gas'ı için ayrıca ücretsiz Arbitrum Sepolia test ETH gerekir. Gerçek coin satın almak bu testin ön şartı değildir.
4. Kurucu bölümünü açın. Kabul yetkilisini `0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD` olarak doğrulayın. Test dağıtımını hazırlayın, inceleyin, MetaMask'te imzalayın. Bu imza test ETH harcar.
5. Başarılı makbuzdaki sözleşme adresini kaydedin. Render Environment bölümüne aşağıdaki dört değeri koyup yeniden dağıtın:

```
PILOT_ENABLED=true
PILOT_RPC_URL=https://sepolia-rollup.arbitrum.io/rpc
PILOT_ESCROW_ADDRESS=<yeni dağıtılan Founding sözleşme adresi>
PILOT_TREASURY_ADDRESS=0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD
```

6. `/pilot/config` artık `enabled:true` döndürmeli. Eski `PAYMENTS_...` ayarları ayrı kalır. Yeni adres yerine eski exact-hash sözleşmesini kullanmayın.
7. Kurucu hesabıyla bir alıcıyı kabul edin. Bu geri alınamaz bir kontenjan kullanır. Alıcı, satıcı ve hakem farklı adresler olmalı; hakem kabul yetkilisi/treasury de olamaz. Testte ayrı hesapların aynı kişi tarafından kullanılması bağımsız hakemlik kanıtı değildir.
8. Alıcı teklif hazırlar, tutarı ve paylaşımı inceler; önce tam USDC izni, ardından bütçe kilitleme işlemini imzalar. Teklif sırasında bütçe kilitlenir. Satıcı ve hakem şartlar metnini aynen girip kabul eder. Metni ve içerik linklerini taraflar ayrıca paylaşır; sunucu bunları kalıcı saklamaz.
9. Teslimatı gönderin, alıcı kabulüyle ödemeyi test edin. Ayrı anlaşmalarla iade, itiraz ve süre aşımı yollarını deneyin. Süre aşımı otomatik para göndermez; ilgili düğme ile zincir işlemi gerekir.

## Test sonucu ve sınırları
Yerelde 40 Python testi geçti: mevcut API/sandbox, eski sözleşme, yeni açık sonuç sözleşmesi, ücretsiz sözleşme ve API'den oluşturulan işlemler. Üç JavaScript kontrol paketi geçti. Tarayıcıda sayfa açılışı ve cüzdansız hata durumu doğrulandı.

Test edilen ücretsiz akışlarda 10 test USDC kilitlenince başarıda satıcı 10 alır; hizmet/hakem ücreti 0'dır. İadede alıcı 10 alır. Hakem süresi aşımında önceden kabul edilen paylaşım uygulanır; örneğin %40 satıcı payında satıcı 4, alıcı 6 alır. Bu paylaşım doğru tarafı belirleyen bir kalite denetimi değildir.

Bu sonuçlar yerel test zincirindendir. Paket henüz GitHub/Render'a yüklenmedi ve Arbitrum Sepolia üzerinde cüzdanla uçtan uca tamamlanmadı. Test ağı kilidi korunuyor; ana ağ ve gerçek para tahsilatı açılmadı. Sunucuya ait koşullu `PILOT_ENABLED` bayrağı ön yüz/API hazırlığını kapatabilir, dağıtılan sözleşmenin zincirdeki işlemlerini durdurmaz.

Bekleyen işlemin hash'i sekme oturumunda saklanır. Makbuz belirsizse tekrar gönderim engellenir. Cüzdan hash vermeden hata döndürürse otomatik açma yoktur; MetaMask etkinlik geçmişi incelenmelidir. Aynı işlem için yeni sekmeden yeniden deneme yapmayın.
