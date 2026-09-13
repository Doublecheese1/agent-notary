# Founding 50 — yayın ve operasyon notu

## Kabul edilen teklif
İlk 50 kabul edilen katılımcıya pilot boyunca AgentNotary komisyonu ve sabit hizmet ücreti yok. Gelecekteki ücretli sürüm ayrı teklif olacak; bu sözleşmede ücret artırma işlevi yok. Satıcının iş bedeli ve ağ gas maliyeti ücretsiz değildir. Pilot hakem ücreti de sıfır; hakemin ücretsiz görevi kabul etmesi gerekir.

## Hazır olan / olmayan
- Ayrı `AgentNotaryFoundingEscrow.sol`: test ağı koruması, sıfır ücret, en fazla 50 alıcı cüzdanı. Treasury yalnızca katılımcı kabul eder; üyeliği geri alamaz, ücret değiştiremez ve fon çekemez. Bu yeni kabul yetkisi mevcut sözleşmelere eklenmedi.
- Başvurular manuel değerlendirilir; 50 cüzdan, 50 farklı kişi olduğunun kanıtı değildir. Aynı kişi tekrar başvurursa kabul edilmemeli. Kabul yetkilisinin aktif olması gerekir.
- `/founding50`: yayınlanmaya hazır yerel tanıtım sayfası. GitHub Issues başvuru bağlantısı, başvuruyu kamuya açık yapar. Issues kapalıysa depo ayarlarından açılmadan bu kanal çalışmaz.
- `/play` ve `/payments` mevcut davranışını korur; yeni ücretsiz sözleşmeye bağlı DEĞİLDİR. Eski demo ücretlerini ücretsiz pilot sonucu diye sunmayın.
- Yeni sözleşme derlendi ve yerel testlerden geçti. Henüz kamuya açık ağa dağıtılmadı, ödeme arayüzü/API entegrasyonu /pilot altında yerelde tamamlandı, bağımsız güvenlik incelemesi yapılmadı.

## Pazartesi yayın sırası
1. Bu paketin eklemelerini GitHub'a aktarın; Render dağıtımından sonra `/founding50` ve `/play` yanıtlarını doğrulayın.
2. GitHub Issues açık mı, başvuru bağlantısı çalışıyor mu kontrol edin. Kabul listesi tutun; henüz zincire kabul edilmiş gibi bildirim göndermeyin.
3. Önce tek bir ilgili geliştirici topluluğunda paylaşın. Topluluk kendi tanıtımını yasaklıyorsa paylaşmayın. Aynı metni farklı başlıklara seri yorum olarak göndermeyin. Projenin kurucusu olduğunuzu açıkça belirtin.
4. Gerçek ödeme açılmadan önce yeni /pilot ekranını yükleyin; test ağında cüzdan imzalarıyla uçtan uca kabul/itiraz/iade ve süre aşımı akışlarını tamamlayın.
5. Ana ağ için token/ağ doğrulaması, sözleşme güvenlik incelemesi, yetkili kabul cüzdanı ve gerçek hakem operasyonu tamamlanmalı. Mevcut test ağı kilidini kaldırmak tek başına bu işleri tamamlamaz. Dağıtım ve kabul işlemleri cüzdan imzası gerektirir; private key sunucuya konulmaz.

Şu an dürüst yayın: ücretsiz sandbox ve pilot başvuruları. “Gerçek USDC escrow açık” duyurusu bu paketin durumu değildir. Pazartesi gerçek para açılışı henüz doğrulanmış bir teslim tarihi değildir.

## Ücretsiz tanıtım metni (İngilizce)
I'm building AgentNotary, an escrow workflow prototype for agent-to-agent tasks, and I'm looking for 50 founding participants to test it and give feedback.

The wallet-free sandbox lets you explore settlement and refund flows. It uses simulated balances; real-money payments aren't open yet. A separate acceptance/dispute contract is being tested for tasks whose result isn't known in advance.

The founding pilot will charge no AgentNotary percentage or fixed service fees. Seller work and network gas are separate. A paid version may come later as a separate offer.

I'd particularly like feedback from people already delegating paid tasks between agents: how do you define acceptance criteria, and what do you do when a delivery is disputed?

Demo: https://agent-notary-5.onrender.com/play
Source and pilot applications: https://github.com/Doublecheese1/agent-notary

## Kısa paylaşım
Building AgentNotary for agent-to-agent escrow. Looking for 50 founding testers: no protocol service fees during the pilot. Wallet-free sandbox available; real-money payments are not open yet. Seller costs and gas are separate. Try it and tell me where your agent workflow breaks: https://agent-notary-5.onrender.com/play

Bu metinler taslaktır; henüz hiçbir platforma gönderilmedi. Ücretli reklam bütçesi sıfır.
