# AgentSolis bağımsız web sitesi, ürün anlatımı ve SEO incelemesi

Yanıtının ilk satırına mutlaka **İnceleyen: [kendi model adın]** yaz. Canlı sayfaları açmadan ve kaynakları kontrol etmeden varsayım yapma. Erişemediğin her şeyi **DOĞRULANAMADI** diye işaretle.

## İncelenecek ürün

- Ana sayfa: https://agentsolis.solists.com.tr/
- İşlem alanı: https://agentsolis.solists.com.tr/mainnet
- Simülasyon: https://agentsolis.solists.com.tr/play
- Founding 50: https://agentsolis.solists.com.tr/mainnet/founding50
- AI agent escrow rehberi: https://agentsolis.solists.com.tr/ai-agent-escrow
- x402 karşılaştırması: https://agentsolis.solists.com.tr/x402-vs-agent-escrow
- Kanıt kontrol listesi: https://agentsolis.solists.com.tr/ai-agent-job-evidence
- Robotlar: https://agentsolis.solists.com.tr/robots.txt
- Site haritası: https://agentsolis.solists.com.tr/sitemap.xml
- Agent card: https://agentsolis.solists.com.tr/.well-known/agent-card.json
- GitHub: Canlı sitedeki GitHub bağlantısından gerçek repoyu bul; bulamazsan DOĞRULANAMADI yaz.

## Dürüst mevcut durum

AgentSolis, AI ajanları arasındaki teslimatlı işler için native USDC escrow ve kanıta dayalı settlement ürünüdür. x402 gibi anlık API ödemesinin yerine geçme iddiası yoktur. Public mainnet para yatırma kapalıdır. Akıllı kontrat dağıtımı, doğrulama, operasyon cüzdanları, bağımsız güvenlik incelemesi ve kapalı canary tamamlanmadan gerçek kullanıcı fonu alınmamalıdır. “Audited”, “zero risk”, “fully autonomous”, “automatic AI judge” veya “mainnet live” gibi kanıtsız ifadeler kullanma.

## Görev

1. Siteyi masaüstü ve mobil ölçülerde gerçekten aç. İlk 5 saniyede ne anladığını yaz.
2. İlk kez gelen şu dört kişinin ayrı ayrı yolunu değerlendir: teknik olmayan alıcı, satıcı ajan geliştiricisi, entegrasyon geliştiricisi, güvenlik konusunda şüpheci kullanıcı.
3. Şunlarla karşılaştır: Arbitova, Escrow.com ve bulduğun en az üç güncel escrow/agent-payment ürünü. Her rakip için gerçek URL, inceleme tarihi ve hangi özelliği doğruladığını yaz.
4. Ana sayfanın şu soruları cevaplayıp cevaplamadığını test et: Ürün nedir? Kim kullanır? x402’den farkı nedir? Para nerede durur? İş nasıl başlar? Satıcı nasıl katılır? Ücret nedir? Anlaşmazlık olursa ne olur? Bugün gerçek para kabul ediliyor mu?
5. “Agree → Lock → Deliver → Settle” anlatımını, orbit görselini, Buyer/Seller butonlarını, gerçek örnek eksikliğini ve mobil görünümü değerlendir. Daha iyi bir illüstrasyon gerekiyorsa metin tarifini ve yerleşimini ver; rakip görselini kopyalama.
6. Ana işlem ekranında kullanıcının hata yapabileceği veya anlamayacağı her noktayı adım adım bul.
7. Güven katmanını incele: kontrat adresi ve doğrulama, ağ/token, ücret, süreler, dispute yolu, fonların saklanması, yönetici yetkileri, audit/canary durumu, privacy/terms, destek ve hata mesajları.
8. Teknik SEO’yu kontrol et: status code, title, description, canonical, robots, sitemap, schema, iç bağlantılar, sosyal paylaşım görseli, performans, erişilebilirlik, duplicate/thin content ve marka tutarlılığı.
9. İçerik stratejisi öner: satın alma niyeti yüksek 15 İngilizce arama konusu; her biri için arama niyeti, başlık, hedef kullanıcı ve AgentSolis’e doğal bağlantı.
10. Backlink ve dağıtım planı öner: Arbitrum, USDC, AutoGen, CrewAI, LangGraph, MCP, x402, GitHub, Reddit, Hacker News ve ürün dizinleri. Her kanalın güncel kurallarını doğrula; spam veya sahte hesap önermeden hangi teknik içeriğin paylaşılacağını yaz.
11. AgentSolis’in gerçek ve savunulabilir farkını tek cümlede yaz. Kanıtlanmamış üstünlük veya “ilk/tek” iddiası kullanma.
12. Tüm önerileri şu şekilde sırala:
   - P0: lansman veya para güvenliği için zorunlu
   - P1: ilk ziyaretçinin anlaması ve dönüşüm için gerekli
   - P2: SEO ve büyüme için gerekli
   Her öneride dosya/sayfa, somut değişiklik, bitiş kriteri ve risk belirt.

## Çıktı biçimi

- İlk satır: İnceleyen adı
- 10 üzerinden puanlar: 5 saniyede anlaşılma, UX, mobil, güven, teknik açıklık, SEO, dönüşüm
- Doğrulanmış artılar
- Doğrulanmış sorunlar
- Rakip karşılaştırma tablosu
- P0/P1/P2 düzeltme listesi
- Önerilen yeni ana sayfa sırası ve tam İngilizce hero metni
- Önerilen illüstrasyon tarifi
- 15 içerik konusu
- Kanal bazlı backlink/dağıtım planı
- GO / CONDITIONAL GO / NO-GO kararı; arayüz yayını ve gerçek para kabulü için ayrı ayrı

Kod değiştirme, hesap açma, paylaşım yapma, alan adı satın alma veya para kabulünü açma. Yalnızca inceleme ve kanıta dayalı öneri ver.
