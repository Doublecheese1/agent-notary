# AgentSolis Safe kurulumu

Üç Safe de **Arbitrum One** üzerinde, aynı üç kurucu adresle ve **2/3** onay eşiğiyle hazırlanacaktır.

| Safe adı | Görevi |
| --- | --- |
| AgentSolis Treasury | Protokol ücretlerini almak ve kasa transferlerini onaylamak |
| AgentSolis Operations | Kabul, erişim, duraklatma ve gelecekteki resolver değişikliklerini onaylamak |
| AgentSolis Human Review | İnsan incelemesine yükseltilen anlaşmazlık kararlarını onaylamak |

## Sahipler

1. Account 1 — `0x6f0e740A38C80036b8B0e5C613725B047BcDa4BD`
2. Seller — `0x1Fb26508Ab8467beb0a27714772868d8ea2dDDf2`
3. Arbitrator — `0x2113caE8042E8fCf837498Eb3297D8563D92Dc2A`

Her işlemde bu üç adresten herhangi ikisi onay vermelidir. Safe oluşturulurken ağ, isim, üç sahip ve eşik cüzdan ekranında tekrar kontrol edilmelidir.

## Güvenlik sınırı

Bu üç hesap aynı kurtarma kelimesinden veya aynı cihazdan üretilmişse kurucu canary testi için kullanılabilir; halka açık fonlar açılmadan önce en az bir bağımsız kişi veya ayrı güvenli cihaz tarafından kontrol edilen sahip eklenmelidir. Kurtarma kelimesi veya özel anahtar hiçbir dosyaya, siteye ya da sohbet ekranına yazılmamalıdır.

Oluşturulan üç Safe adresi önce `release/safe-setup.json`, sonra `release/mainnet-release.json` içine yazılacak; zincirde `getThreshold() >= 2` ve sahip listeleri doğrulanmadan kontrat dağıtılmayacaktır.
