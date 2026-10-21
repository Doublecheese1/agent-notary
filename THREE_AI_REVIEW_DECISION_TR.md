# AgentNotary — Gemini, Grok ve Claude Son İnceleme Kararı

Tarih: 19 Eylül 2026

## Nihai karar

Üç raporun ortak kararı **CONDITIONAL GO**: kod kapalı mainnet dağıtımı ve kurucunun küçük canary işlemi için hazırdır; bağımsız güvenlik incelemesi, gerçek Safe yapılandırması, üç bağımsız doğrulayıcı ve canary tamamlanmadan yabancı kullanıcı fonlarına açılmamalıdır.

## Kodla doğrulanan düzeltmeler

- Referans doğrulayıcı HTTP çağrısı yapmaz. Yerel olarak verilen manifest ve içerik baytlarını deterministik biçimde denetler.
- Kanıt sonucu `dealId`, kontrat, zincir, içerik hash'i, manifest hash'i, politika hash'i, karar, nonce ve son kullanım zamanına bağlı EIP-712 imzalarıyla korunur.
- Kontratta `Pausable` zaten vardır ve pause yalnızca yeni anlaşmaları durdurur; mevcut fonların çıkışları çalışır.
- Buyer Review sonucunda kaybeden tarafın rezervi resolver ücretini öder; alıcı haklıysa kendi rezervini geri alır.
- Founding 50 süresi kayıt anında değil, ilk fonlanan mainnet anlaşmasının atomik işlemi içinde başlar.
- Pazarlama metinlerinde “AI judge”, “zero fraud”, “trustless” veya “audited” iddiası yoktur.

Bu nedenle Gemini raporundaki HTTP indirme, eksik Pausable, replay bağının bulunmaması ve hakem ücretinin her durumda alıcıya yüklenmesi maddeleri mevcut paket için geçerli değildir.

## Raporların ortaya çıkardığı gerçek boşluklar ve yapılan son düzeltmeler

1. Otomatik doğrulama için ayrı `/mainnet/validator` konsolu eklendi. Üç bağımsız cüzdan aynı EIP-712 sonucu ayrı ayrı imzalayabilir; relay en az iki imzayı zincire taşır. Uygulama private key istemez veya saklamaz.
2. Yerel ve ağsız doğrulama çalıştırıcısı `validator/run_validation.py` eklendi.
3. Yeni para girişini kapatan bayrağın mevcut kilitli anlaşmaların teslimat, doğrulama ve iade işlemlerini de engellemesi düzeltildi. Kapı artık yalnızca yeni fonlamayı durdurur.
4. Hızlı çift tıklamayla iki cüzdan isteği açılabilecek kısa pencere kapatıldı.
5. Sayfa yenilendikten sonra zincirde onaylanmış USDC allowance tekrar okunuyor; kullanıcı gereksiz ikinci approval'a zorlanmıyor.
6. Resolver rotasyonundaki sürekli güven garantisi kapatıldı. Arbitrum One üzerinde yeni Automatic validator yalnızca mevcut immutable quorum ile aynı runtime koduna sahipse; yeni Review Arbitrator yalnızca mevcut Safe ile aynı runtime koduna ve en az iki imza eşiğine sahipse atanabilir. Mevcut anlaşmalar zaten fonlandıkları resolver adresini korur.
7. Deployer/gas cüzdanı `0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD` olarak backend, deployment UI ve release manifest içinde eşleştirildi. Önceki `0x21a7…c26D` adresinin BtcTurk yatırma adresi olduğu doğrulandığı için üretim yapılandırmasından çıkarıldı.
8. Eski `FOUNDING50_TR.md` belgesinin testnet arşivi olduğu dosyanın başında açıklandı; güncel mainnet teklifiyle karıştırılması önlendi.

## Değiştirilmeyen kararlar

- Yumuşatılmış turkuaz–mavi geçiş (`#A8E8D6` → `#6FC3E0`, dekoratif `#3A6FC4`) yalnızca Founding 50/landing tanıtım alanında kalır; koyu mavi bölgenin üzerine metin yerleştirilmez.
- Krem–pine–ink paleti para işlem ekranında kalır. Grok ve Claude bu ayrımı destekledi; koyu slate tema zorunlu değildir.
- 2/3 doğrulayıcı modeli korunur. İki imzacının anlaşması bütün 2/3 sistemlerinde güven varsayımıdır; imzacılar ayrı kişi/kurum, ayrı cihaz ve ayrı seed kullanmalıdır.
- Üç INCONCLUSIVE sonrasında erken idari müdahale eklenmez. Fonlar önceden kabul edilen deadline sonunda permissionless fallback ile çıkar; bu süre açıkça gösterilmelidir.

## Son doğrulama

- Son resolver rotasyon düzeltmesinden sonra Solidity 0.8.30 derlemesi başarılı.
- Son mainnet tarayıcı koruma testi başarılı.
- Daha önceki tam koşumda 30 uygulama/API ve 35 kontrat/SDK/doğrulayıcı testi başarılıydı.
- Rotasyon düzeltmesinden sonraki Python tekrar koşumu Windows'un yerel bağımlılık dosyalarına erişimi engellemesi nedeniyle başlamadı; bu bir test başarısızlığı değildir ancak GitHub Linux CI yeşil olmadan dağıtım yapılmayacaktır.

Bu kontroller bağımsız audit değildir.

## Para kabulünden önce kalan dış adımlar

1. Treasury Safe, Operations Safe ve review arbitrator Safe'i gerçek multisig olarak oluştur ve sahiplerini doğrula.
2. Üç validator imzacısını ayrı kişi/kurum, ayrı cihaz ve ayrı seed ile belirle; isimleri ve çalışma kuralını yayımla.
3. Bağımsız kontrat incelemesi/audit başvurusunu tamamla.
4. ETH geldikten sonra quorum ve escrow kontratlarını Arbitrum One'a dağıt, Arbiscan'da kaynak ve bytecode'u doğrula.
5. `MAINNET_ENABLED=true`, `MAINNET_ACCEPTING_FUNDS=false` ile yalnızca okuma ve kurucu işlemlerini aç.
6. Tek bir 10 USDC Automatic canary yap; PASS, FAIL ve timeout kayıtlarını/bakiyelerini kontrol et.
7. Sorun yoksa önce en fazla beş davetli buyer ile küçük kapalı beta aç; halka açık erişimi daha sonra değerlendir.
