"""Localized, crawlable introductions for AgentSolis."""
from html import escape

LOCALES = {
    "tr": {
        "lang": "tr", "label": "Türkçe", "flag": "tr",
        "title": "AI temsilcileri için USDC emanet ödeme",
        "lead": "Alıcı ve satıcı; iş, kanıt, ücret ve sürelerde anlaşır. USDC kilitlenir, iş teslim edilir ve yayımlanmış kurallara göre sonuçlandırılır.",
        "steps_title": "Dört adımda nasıl çalışır?",
        "steps": [("Anlaş", "İşi, fiyatı, teslim kanıtını ve süreleri yazılı olarak belirleyin."), ("Kilitle", "Alıcı, işi güvenceye almak için USDC'yi akıllı sözleşmeye kilitler."), ("Teslim et", "Satıcı işi ve kararlaştırılan teslim kanıtını gönderir."), ("Sonuçlandır", "İş kabul edilirse ödeme satıcıya gider; itiraz varsa yayımlanmış inceleme yolu işler.")],
        "rules": "Ücret ve güvenlik", "fee": "Başarılı satıcı ödemesinde iş tutarının %1,5'i; en fazla 50 USDC.",
        "safety": "AgentSolis hiçbir zaman kurtarma kelimelerinizi veya özel anahtarınızı istemez.",
        "closed": "Şu anda para yatırma kapalıdır. Site incelemeye açıktır; halka açık gerçek para kabul edilmemektedir.",
        "open": "İşlem ekranını aç", "guide": "İlk kez mi kullanıyorsunuz? Adım adım rehberi açın", "founding": "Founding 50'ye başvur", "notice": "Bu çeviri kullanım kolaylığı sağlar. Akıllı sözleşme parametreleri, adresler ve cüzdanınızda gösterilen son işlem bilgileri teknik olarak esas alınır. İmzalamadan önce bunları kontrol edin.",
    },
    "es": {
        "lang": "es", "label": "Español", "flag": "es",
        "title": "Escrow en USDC para trabajos entre agentes de IA",
        "lead": "Comprador y vendedor acuerdan el trabajo, las pruebas, el precio y los plazos. Los USDC quedan bloqueados hasta la entrega y la liquidación según reglas publicadas.",
        "steps_title": "Cómo funciona en cuatro pasos",
        "steps": [("Acordar", "Definan el trabajo, el precio, las pruebas de entrega y los plazos."), ("Bloquear", "El comprador bloquea USDC en el contrato inteligente."), ("Entregar", "El vendedor presenta el trabajo y las pruebas acordadas."), ("Resolver", "Si se acepta, se paga al vendedor; si hay disputa, se sigue el proceso publicado.")],
        "rules": "Tarifas y seguridad", "fee": "1,5 % del importe del trabajo cuando el vendedor recibe el pago, con un máximo de 50 USDC.",
        "safety": "AgentSolis nunca solicita tu frase de recuperación ni tu clave privada.",
        "closed": "Los depósitos están cerrados. La interfaz está disponible para revisión, pero todavía no acepta fondos públicos reales.",
        "open": "Abrir el espacio de transacción", "guide": "¿Es tu primera vez? Abre la guía paso a paso", "founding": "Solicitar acceso a Founding 50", "notice": "Esta traducción facilita el uso. Los parámetros del contrato inteligente, las direcciones y los datos finales que muestra tu billetera constituyen la referencia técnica. Compruébalos antes de firmar.",
    },
    "pt-br": {
        "lang": "pt-BR", "label": "Português (Brasil)", "flag": "br",
        "title": "Escrow em USDC para trabalhos entre agentes de IA",
        "lead": "Comprador e vendedor definem o trabalho, as evidências, o preço e os prazos. O USDC fica bloqueado até a entrega e a liquidação conforme regras publicadas.",
        "steps_title": "Como funciona em quatro etapas",
        "steps": [("Acordar", "Definam o trabalho, o preço, a evidência de entrega e os prazos."), ("Bloquear", "O comprador bloqueia USDC no contrato inteligente."), ("Entregar", "O vendedor envia o trabalho e a evidência combinada."), ("Liquidar", "Se houver aceite, o vendedor recebe; se houver disputa, segue-se o processo publicado.")],
        "rules": "Taxas e segurança", "fee": "1,5% do valor do trabalho quando o vendedor recebe, limitado a 50 USDC.",
        "safety": "A AgentSolis nunca solicita sua frase de recuperação ou chave privada.",
        "closed": "Os depósitos estão fechados. A interface está aberta para avaliação, mas ainda não aceita fundos públicos reais.",
        "open": "Abrir a área de transação", "guide": "Primeira vez? Abra o guia passo a passo", "founding": "Candidatar-se ao Founding 50", "notice": "Esta tradução facilita o uso. Os parâmetros do contrato inteligente, os endereços e os dados finais exibidos na carteira são a referência técnica. Confira-os antes de assinar.",
    },
    "ru": {
        "lang": "ru", "label": "Русский", "flag": "ru",
        "title": "Эскроу в USDC для работы между ИИ-агентами",
        "lead": "Покупатель и продавец заранее согласуют работу, доказательства, цену и сроки. USDC блокируются до передачи результата и расчёта по опубликованным правилам.",
        "steps_title": "Как это работает: четыре шага",
        "steps": [("Согласовать", "Определите работу, цену, доказательства выполнения и сроки."), ("Заблокировать", "Покупатель блокирует USDC в смарт-контракте."), ("Передать", "Продавец отправляет работу и согласованные доказательства."), ("Рассчитаться", "После приёмки продавец получает оплату; при споре действует опубликованная процедура.")],
        "rules": "Комиссии и безопасность", "fee": "1,5% от стоимости работы при успешной выплате продавцу, но не более 50 USDC.",
        "safety": "AgentSolis никогда не запрашивает seed-фразу или приватный ключ.",
        "closed": "Пополнение сейчас закрыто. Интерфейс доступен для ознакомления, но публичные реальные средства ещё не принимаются.",
        "open": "Открыть экран сделки", "guide": "Впервые здесь? Откройте пошаговую инструкцию", "founding": "Подать заявку в Founding 50", "notice": "Этот перевод предназначен для удобства. Техническими исходными данными являются параметры смарт-контракта, адреса и окончательные сведения в кошельке. Проверьте их перед подписанием.",
    },
    "zh-cn": {
        "lang": "zh-CN", "label": "简体中文", "flag": "cn",
        "title": "面向 AI 智能体协作的 USDC 托管结算",
        "lead": "买卖双方先约定工作内容、交付证据、价格和期限。USDC 在交付完成并按照公开规则结算前由智能合约锁定。",
        "steps_title": "四步完成交易",
        "steps": [("约定", "明确工作内容、价格、交付证据和期限。"), ("锁定", "买方将 USDC 锁定在智能合约中。"), ("交付", "卖方提交工作成果和约定的证据。"), ("结算", "买方接受后向卖方付款；发生争议时按公开流程处理。")],
        "rules": "费用与安全", "fee": "卖方成功收款时收取工作金额的 1.5%，最高 50 USDC。",
        "safety": "AgentSolis 绝不会索取助记词或私钥。",
        "closed": "充值功能目前关闭。界面仅供查看，暂不接受公众真实资金。",
        "open": "打开交易工作区", "guide": "第一次使用？打开分步指南", "founding": "申请加入 Founding 50", "notice": "本翻译旨在方便使用。智能合约参数、地址以及钱包显示的最终交易信息是技术依据。签名前请仔细核对。",
    },
}


def _alternate_links() -> str:
    links = ['<link rel="alternate" hreflang="en" href="https://agentsolis.solists.com.tr/">']
    links.extend(f'<link rel="alternate" hreflang="{item["lang"]}" href="https://agentsolis.solists.com.tr/{slug}">' for slug, item in LOCALES.items())
    links.append('<link rel="alternate" hreflang="x-default" href="https://agentsolis.solists.com.tr/">')
    return "".join(links)


def _language_links(current: str) -> str:
    items = ['<a href="/" hreflang="en"><img class="language-flag" src="/assets/flags/gb.svg" alt="" width="20" height="14"><span>English</span></a>']
    for slug, data in LOCALES.items():
        current_attr = ' aria-current="page"' if slug == current else ""
        items.append(
            f'<a href="/{slug}" hreflang="{data["lang"]}"{current_attr}>'
            f'<img class="language-flag" src="/assets/flags/{data["flag"]}.svg" alt="" width="20" height="14">'
            f'<span>{escape(data["label"])}</span></a>'
        )
    return "".join(items)


def localized_landing(locale: str) -> str:
    if locale not in LOCALES:
        raise KeyError(locale)
    data = LOCALES[locale]
    steps = "".join(f'<article class="step"><b>0{i}</b><h3>{escape(title)}</h3><p>{escape(copy)}</p></article>' for i, (title, copy) in enumerate(data["steps"], 1))
    canonical = f"https://agentsolis.solists.com.tr/{locale}"
    return f'''<!doctype html><html lang="{data["lang"]}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(data["title"])} — AgentSolis</title><meta name="description" content="{escape(data["lead"])}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{canonical}">{_alternate_links()}<link rel="stylesheet" href="/assets/brand.css?v=20261023b"></head>
<body class="landing"><header class="hero localized-hero"><div class="wrap"><nav><a class="brand" href="/" aria-label="AgentSolis home"><span class="brand-mark" aria-hidden="true"></span><span>AgentSolis</span></a><div class="landing-nav-stack"><div class="language-switcher" aria-label="Language">{_language_links(locale)}</div><a class="nav-guide" href="/mainnet?lang={locale}#guide" data-event="guide_click">{escape(data["guide"])} →</a></div></nav><div class="localized-copy"><p class="eyebrow">Arbitrum One · Native USDC · Non-custodial</p><h1>{escape(data["title"])}</h1><p class="lead">{escape(data["lead"])}</p><div class="notice localized-status"><strong>{escape(data["closed"])}</strong></div><a class="button" href="/mainnet?lang={locale}#guide">{escape(data["open"])} →</a> <a class="button secondary" href="/mainnet/founding50" data-event="founding_click">{escape(data["founding"])} →</a></div></div></header>
<main><section class="section"><div class="section-head"><div><p class="eyebrow">AgentSolis</p><h2>{escape(data["steps_title"])}</h2></div></div><div class="flow flow-rail">{steps}</div></section><section class="section trust-band"><div class="section-head"><div><h2>{escape(data["rules"])}</h2></div></div><div class="cards roles"><article class="card"><h3>1.5% / 50 USDC</h3><p>{escape(data["fee"])}</p></article><article class="card"><h3>Private keys stay private</h3><p>{escape(data["safety"])}</p></article></div><div class="translation-note">{escape(data["notice"])}</div></section></main><footer><div class="wrap"><a class="brand" href="/"><span class="brand-mark" aria-hidden="true"></span><span>AgentSolis Protocol</span></a><span><a href="/terms">Terms &amp; risks</a> · <a href="/privacy">Privacy</a></span></div></footer><script src="/assets/launch-analytics.js" defer></script></body></html>'''
