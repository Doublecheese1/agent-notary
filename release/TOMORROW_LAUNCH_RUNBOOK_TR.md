# AgentSolis — yarın yalnızca imza gerektiren işler

Hazırlık tarihi: 22 Ekim 2026

Bu listedeki cüzdan onayları dışındaki kod, metin, test, adres şablonu ve güvenlik kapısı hazırlıkları bugün tamamlanmıştır. Seed phrase veya private key hiçbir yere yazılmayacaktır.

## 1. Üç Safe'i oluştur

Ağ: **Arbitrum One**  
Eşik: **3 sahibin 2 onayı**

Sahipler:

1. Account 1 — `0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD`
2. AgentSolis B — `0x9c41A746c6649b36e548cf4D9C5CCe3Ef4648cbA`
3. ARBITRATOR — `0x2113caE8042E8fCf837498Eb3297D8563D92Dc2A` (yalnız kapalı dağıtım ve kurucu canary için geçici C)

Halka açık para açılmadan önce bu geçici C, ayrı kontrol edilen gerçek AgentSolis C ile değiştirilir. Yeni C oluşturulduğunda gelecekteki anlaşmalar için validator quorum ve AI resolver yeniden dağıtılıp escrow'da döndürülür.

Safe adları:

- AgentSolis Treasury
- AgentSolis Operations
- AgentSolis Human Review

Her Safe oluşturulduktan sonra adresi `release/safe-setup.json` ve `release/mainnet-release.json` dosyalarına kaydet. Zincirde kod bulunduğunu, sahipleri ve `getThreshold() = 2` sonucunu doğrula.

## 2. Yalnız deployer hesabını fonla

ETH yalnızca MetaMask **Account 1** adresine, **Arbitrum One ağı üzerinden** gönderilecek:

`0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD`

`0x21a7…c26D` BtcTurk yatırma adresidir; deployer/gas adresi değildir ve buraya gönderim yapılmayacaktır.

22 Ekim 21.32'de resmi Arbitrum RPC ölçümü: gas fiyatı **0,02 gwei**, Account 1 bakiyesi **0 ETH**. Validator quorum tahmini **482.245 gas**, AI resolver tahmini **2.009.818 gas**; bilinen iki kontrat toplamı **2.492.063 gas**.

Yarın ilk aktarım planı: **0,003 ETH**. Bu bir harcama hedefi değildir; kullanılmayan ETH Account 1'de kalır. Üç Safe ile bağımlı kontratlar oluştuktan sonra escrow ve kalan işlemler için cüzdanın canlı `eth_estimateGas` sonucu tekrar kontrol edilir. Tam tahmin ve güvenlik payı kalan bakiyeyi aşarsa yalnız eksik kadar ekleme yapılır.

## 3. Geçici dağıtım kapısını aç

Render ayarları:

```text
MAINNET_ENABLED=false
MAINNET_ACCEPTING_FUNDS=false
MAINNET_DEPLOYMENT_UI=true
MAINNET_OPERATIONS_UI=false
MAINNET_DEPLOYER_ADDRESS=0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD
MAINNET_RPC_URL=<Arbitrum One HTTPS RPC>
MAINNET_TREASURY_SAFE=<Treasury Safe>
MAINNET_OPERATIONS_SAFE=<Operations Safe>
MAINNET_ESCROW_ADDRESS=
```

Para kabulü bu aşamada kapalı kalır.

## 4. Kontratları sırayla dağıt

`/mainnet/setup` ekranında MetaMask Account 1 ile:

1. Validator quorum
2. AI review resolver
3. Escrow

Her işlemde ağın Arbitrum One, gönderenin Account 1 ve rol adreslerinin doğru olduğunu cüzdanda tekrar kontrol et. Bir işlem cevabı kaybolursa ikinci kez göndermeden önce kayıtlı hash'i kontrol et.

Escrow dağıtımından sonra Operations Safe üzerinden resolver'ın `bindEscrow` işlemi hazırlanır ve iki Safe sahibi onaylar.

## 5. Dağıtım sonrası kapıları kapat ve doğrula

Önce:

```text
MAINNET_DEPLOYMENT_UI=false
MAINNET_OPERATIONS_UI=false
MAINNET_ENABLED=true
MAINNET_ACCEPTING_FUNDS=false
```

Ardından:

- Kontrat kaynaklarını Arbiscan'de doğrula.
- Native USDC, Treasury Safe, Operations Safe, quorum ve resolver adreslerini zincirden karşılaştır.
- Kontratın yeni anlaşmalar için başlangıçta paused olduğunu doğrula.
- 10 USDC Automatic canary işlemini yalnız kendi hesaplarınla yap.
- Event ve USDC bakiyelerini beklenen sonuçla karşılaştır.

## Halka açık para için ayrı şart

Canary başarılı olsa bile bağımsız güvenlik incelemesi tamamlanmadan, kritik/yüksek kasa bulguları kapanmadan ve en az bir Safe/validator imzacısı bağımsız hale gelmeden `MAINNET_ACCEPTING_FUNDS=true` yapılmaz.
