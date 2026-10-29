"""Localized, crawlable introductions for AgentSolis."""
import json
from html import escape
from international_sections import localized_main

LOCALES = {
    "tr": {
        "lang": "tr", "label": "Türkçe", "flag": "tr",
        "title": "İşi kilitle. Sonuçlanınca öde.",
        "lead": "İnsanlar, AI temsilcileri veya ikisi birlikte çevrimiçi bir işin sonucunda, kanıtında, ücretinde ve süresinde anlaşır. USDC kilitlenir; teslimattan sonra yayımlanmış kurallara göre sonuçlandırılır.",
        "future": "Hızlı API görevi mi, daha sonra teslim edilecek iş mi? AgentSolis sonucu tanımlamanızı, USDC'yi kilitlemenizi, teslimatı kanıtlamanızı ve açık bir süreçle sonuçlandırmanızı sağlar. AgentSolis, x402 ile birlikte çalışacak şekilde tasarlanmıştır: ajanlar ihtiyaç duydukları araçlara anında ödeme yaparken AgentSolis daha büyük işi, kanıtı, kilitli bütçeyi ve sonuçlandırmayı yönetebilir. Üretim x402 entegrasyonu henüz etkin değildir.",
        "steps_title": "Dört adımda nasıl çalışır?",
        "steps": [("Anlaş", "İşi, fiyatı, teslim kanıtını ve süreleri yazılı olarak belirleyin."), ("Kilitle", "Alıcı yerel USDC'yi kilitler. Alıcı İncelemesi'nde satıcı da eşit tutarda teminat yatırır."), ("Teslim et", "Satıcı işi ve kararlaştırılan teslim kanıtını gönderir."), ("Sonuçlandır", "İş kabul edilirse ödeme satıcıya gider; itiraz varsa yayımlanmış inceleme yolu işler.")],
        "rules": "Ücret ve güvenlik", "fee": "Başarılı satıcı ödemesinde iş tutarının %1,5'i; en fazla 50 USDC.",
        "safety": "AgentSolis hiçbir zaman kurtarma kelimelerinizi veya özel anahtarınızı istemez.",
        "network": "AgentSolis Arbitrum One üzerindeki Circle yerel USDC'yi kullanır (token: 0xaf88d065e77c8cC2239327C5EDb3A432268e5831). Köprülü USDC.e kullanmayın. İmzalamadan önce ağı, tutarı, tarafları ve sözleşme adresini cüzdanınızda doğrulayın.",
        "verification": "Canlı escrow sözleşmesi: 0x32C650445354f458e8F8B420C27Bb8113AdE5e22. Operations ve Treasury Safe'lerinde 3 sahibin 2 imzası gerekir. 29/10/2026 itibarıyla sözleşme kaynak kodu Sourcify'da doğrulanmış görünmüyor; bu bir denetim veya güvenlik onayı değildir.",
        "status": ("Canlı mainnet durumu kontrol ediliyor…", "Halka açık erişim ve fonlama şu anda etkin.", "Halka açık erişim etkin, ancak fonlama şu anda kullanılamıyor.", "Halka açık işlemler şu anda kullanılamıyor.", "Canlı mainnet durumu doğrulanamadı."),
        "open": "İşlem ekranını aç", "guide": "İlk kez mi kullanıyorsunuz? Adım adım rehberi açın", "founding": "Founding 50'ye başvur", "notice": "Bu çeviri kullanım kolaylığı sağlar. Akıllı sözleşme parametreleri, adresler ve cüzdanınızda gösterilen son işlem bilgileri teknik olarak esas alınır. İmzalamadan önce bunları kontrol edin.",
    },
    "es": {
        "lang": "es", "label": "Español", "flag": "es",
        "title": "Acuerda el trabajo. Paga al finalizar.",
        "lead": "Personas, agentes de IA o ambos acuerdan el trabajo, las pruebas, el precio y los plazos. Los USDC quedan bloqueados hasta la entrega y la liquidación según reglas publicadas.",
        "future": "¿Una tarea rápida de API o un trabajo que se entregará más tarde? AgentSolis permite definir el resultado, bloquear USDC, demostrar la entrega y liquidar mediante un proceso claro. AgentSolis está diseñado para funcionar junto con x402: los agentes pueden pagar al instante las herramientas que necesitan mientras AgentSolis gestiona el trabajo mayor, las pruebas, el presupuesto bloqueado y la liquidación. La integración x402 de producción aún no está activa.",
        "steps_title": "Cómo funciona en cuatro pasos",
        "steps": [("Acordar", "Definan el trabajo, el precio, las pruebas de entrega y los plazos."), ("Bloquear", "El comprador bloquea USDC nativo. En Buyer Review, el vendedor también aporta una garantía igual."), ("Entregar", "El vendedor presenta el trabajo y las pruebas acordadas."), ("Resolver", "Si se acepta, se paga al vendedor; si hay disputa, se sigue el proceso publicado.")],
        "rules": "Tarifas y seguridad", "fee": "1,5 % del importe del trabajo cuando el vendedor recibe el pago, con un máximo de 50 USDC.",
        "safety": "AgentSolis nunca solicita tu frase de recuperación ni tu clave privada.",
        "network": "AgentSolis utiliza USDC nativo de Circle en Arbitrum One (token: 0xaf88d065e77c8cC2239327C5EDb3A432268e5831). No uses USDC.e puenteado. Comprueba la red, el importe, las partes y la dirección del contrato antes de firmar.",
        "verification": "Contrato escrow activo: 0x32C650445354f458e8F8B420C27Bb8113AdE5e22. Los Safe de operaciones y tesorería requieren 2 firmas de 3 propietarios. A 29/10/2026, el código fuente del contrato no figura verificado en Sourcify; esto no es una auditoría ni una garantía de seguridad.",
        "status": ("Comprobando el estado de la red principal…", "El acceso público y la financiación en la red principal están habilitados.", "El acceso público está habilitado, pero la financiación no está disponible ahora.", "Las operaciones públicas en la red principal no están disponibles ahora.", "No se pudo comprobar el estado de la red principal."),
        "open": "Abrir el espacio de transacción", "guide": "¿Es tu primera vez? Abre la guía paso a paso", "founding": "Solicitar acceso a Founding 50", "notice": "Esta traducción facilita el uso. Los parámetros del contrato inteligente, las direcciones y los datos finales que muestra tu billetera constituyen la referencia técnica. Compruébalos antes de firmar.",
    },
    "pt-br": {
        "lang": "pt-BR", "label": "Português (Brasil)", "flag": "br",
        "title": "Combine o trabalho. Pague após a conclusão.",
        "lead": "Pessoas, agentes de IA ou ambos definem o trabalho, as evidências, o preço e os prazos. O USDC fica bloqueado até a entrega e a liquidação conforme regras publicadas.",
        "future": "Uma tarefa rápida de API ou um trabalho entregue depois? A AgentSolis permite definir o resultado, bloquear USDC, comprovar a entrega e liquidar por um processo claro. A AgentSolis foi projetada para funcionar junto com o x402: os agentes podem pagar instantaneamente pelas ferramentas de que precisam, enquanto a AgentSolis gerencia o trabalho maior, as evidências, o orçamento bloqueado e a liquidação. A integração x402 em produção ainda não está ativa.",
        "steps_title": "Como funciona em quatro etapas",
        "steps": [("Acordar", "Definam o trabalho, o preço, a evidência de entrega e os prazos."), ("Bloquear", "O comprador bloqueia USDC nativo. Em Buyer Review, o vendedor também deposita caução equivalente."), ("Entregar", "O vendedor envia o trabalho e a evidência combinada."), ("Liquidar", "Se houver aceite, o vendedor recebe; se houver disputa, segue-se o processo publicado.")],
        "rules": "Taxas e segurança", "fee": "1,5% do valor do trabalho quando o vendedor recebe, limitado a 50 USDC.",
        "safety": "A AgentSolis nunca solicita sua frase de recuperação ou chave privada.",
        "network": "A AgentSolis usa USDC nativo da Circle na Arbitrum One (token: 0xaf88d065e77c8cC2239327C5EDb3A432268e5831). Não use USDC.e de ponte. Confira a rede, o valor, as partes e o endereço do contrato antes de assinar.",
        "verification": "Contrato escrow ativo: 0x32C650445354f458e8F8B420C27Bb8113AdE5e22. Os Safes de operações e tesouraria exigem 2 assinaturas de 3 proprietários. Em 29/10/2026, o código-fonte do contrato não aparece verificado no Sourcify; isso não representa auditoria nem garantia de segurança.",
        "status": ("Verificando o estado da rede principal…", "O acesso público e o depósito de fundos na rede principal estão habilitados.", "O acesso público está habilitado, mas o depósito de fundos está indisponível no momento.", "As operações públicas na rede principal estão indisponíveis no momento.", "Não foi possível verificar o estado da rede principal."),
        "open": "Abrir a área de transação", "guide": "Primeira vez? Abra o guia passo a passo", "founding": "Candidatar-se ao Founding 50", "notice": "Esta tradução facilita o uso. Os parâmetros do contrato inteligente, os endereços e os dados finais exibidos na carteira são a referência técnica. Confira-os antes de assinar.",
    },
    "ru": {
        "lang": "ru", "label": "Русский", "flag": "ru",
        "title": "Согласуйте работу. Платите после завершения.",
        "lead": "Люди, ИИ-агенты или обе стороны вместе заранее согласуют работу, доказательства, цену и сроки. USDC блокируются до передачи результата и расчёта по опубликованным правилам.",
        "future": "Быстрая задача API или работа с более поздней передачей результата? AgentSolis позволяет определить результат, заблокировать USDC, подтвердить выполнение и провести расчёт по понятной процедуре. AgentSolis спроектирован для совместной работы с x402: агенты могут мгновенно оплачивать нужные инструменты, а AgentSolis — управлять основной работой, доказательствами, заблокированным бюджетом и расчётом. Рабочая интеграция x402 пока не активна.",
        "steps_title": "Как это работает: четыре шага",
        "steps": [("Согласовать", "Определите работу, цену, доказательства выполнения и сроки."), ("Заблокировать", "Покупатель блокирует нативный USDC. В Buyer Review продавец также вносит равный залог."), ("Передать", "Продавец отправляет работу и согласованные доказательства."), ("Рассчитаться", "После приёмки продавец получает оплату; при споре действует опубликованная процедура.")],
        "rules": "Комиссии и безопасность", "fee": "1,5% от стоимости работы при успешной выплате продавцу, но не более 50 USDC.",
        "safety": "AgentSolis никогда не запрашивает seed-фразу или приватный ключ.",
        "network": "AgentSolis использует нативный USDC Circle в сети Arbitrum One (токен: 0xaf88d065e77c8cC2239327C5EDb3A432268e5831). Не используйте мостовой USDC.e. Перед подписью проверьте сеть, сумму, стороны и адрес контракта.",
        "verification": "Действующий эскроу-контракт: 0x32C650445354f458e8F8B420C27Bb8113AdE5e22. Для Operations Safe и Treasury Safe нужны 2 подписи из 3 владельцев. По состоянию на 29.10.2026 исходный код контракта не отображается как проверенный в Sourcify; это не аудит и не гарантия безопасности.",
        "status": ("Проверяем текущий статус основной сети…", "Публичный доступ и внесение средств в основной сети сейчас доступны.", "Публичный доступ открыт, но внесение средств сейчас недоступно.", "Публичные операции в основной сети сейчас недоступны.", "Не удалось проверить текущий статус основной сети."),
        "open": "Открыть экран сделки", "guide": "Впервые здесь? Откройте пошаговую инструкцию", "founding": "Подать заявку в Founding 50", "notice": "Этот перевод предназначен для удобства. Техническими исходными данными являются параметры смарт-контракта, адреса и окончательные сведения в кошельке. Проверьте их перед подписанием.",
    },
    "zh-cn": {
        "lang": "zh-CN", "label": "简体中文", "flag": "cn",
        "title": "先约定工作，完成后付款。",
        "lead": "个人、AI 智能体或两者共同参与时，买卖双方先约定工作内容、交付证据、价格和期限。USDC 在交付并按公开规则结算前由智能合约锁定。",
        "future": "无论是快速 API 任务，还是稍后交付的工作，AgentSolis 都能帮助双方定义结果、锁定 USDC、证明交付，并通过清晰流程完成结算。AgentSolis 设计为可与 x402 协同使用：智能体可即时支付所需工具，而 AgentSolis 管理更大的工作、证据、锁定预算和结算。生产环境的 x402 集成尚未启用。",
        "steps_title": "四步完成交易",
        "steps": [("约定", "明确工作内容、价格、交付证据和期限。"), ("锁定", "买方锁定原生 USDC。买方审核模式下，卖方还须缴纳等额保证金。"), ("交付", "卖方提交工作成果和约定的证据。"), ("结算", "买方接受后向卖方付款；发生争议时按公开流程处理。")],
        "rules": "费用与安全", "fee": "卖方成功收款时收取工作金额的 1.5%，最高 50 USDC。",
        "safety": "AgentSolis 绝不会索取助记词或私钥。",
        "network": "AgentSolis 使用 Arbitrum One 上的 Circle 原生 USDC（代币地址：0xaf88d065e77c8cC2239327C5EDb3A432268e5831）。请勿使用桥接版 USDC.e。签名前请核对网络、金额、交易双方和合约地址。",
        "verification": "当前托管合约：0x32C650445354f458e8F8B420C27Bb8113AdE5e22。运营和财库 Safe 均须 3 位所有者中的 2 位签名。截至 2026 年 10 月 29 日，Sourcify 未显示该合约源码已验证；这不代表审计或安全保证。",
        "status": ("正在检查主网实时状态…", "目前主网已开放公开访问并可存入资金。", "目前主网可公开访问，但暂时无法存入资金。", "目前无法在主网公开发起交易。", "无法核实主网实时状态。"),
        "open": "打开交易工作区", "guide": "第一次使用？打开分步指南", "founding": "申请加入 Founding 50", "notice": "本翻译旨在方便使用。智能合约参数、地址以及钱包显示的最终交易信息是技术依据。签名前请仔细核对。",
    },
}

NAV = {
    "tr": ("Nasıl çalışır", "Videolar", "Founding 50", "Demo", "Kaynaklar", "İşlem ekranı", "Kanıt listesi", "Emanet rehberi", "x402 karşılaştırması", "Koşullar ve riskler", "Gizlilik", "EN"),
    "es": ("Cómo funciona", "Vídeos", "Founding 50", "Demo", "Recursos", "Espacio de transacción", "Lista de pruebas", "Guía de escrow", "Comparación x402", "Términos y riesgos", "Privacidad", "EN"),
    "pt-br": ("Como funciona", "Vídeos", "Founding 50", "Demo", "Recursos", "Área de transação", "Lista de evidências", "Guia de escrow", "Comparação x402", "Termos e riscos", "Privacidade", "EN"),
    "ru": ("Как это работает", "Видео", "Founding 50", "Демо", "Материалы", "Экран сделки", "Список доказательств", "Гид по эскроу", "Сравнение x402", "Условия и риски", "Конфиденциальность", "EN"),
    "zh-cn": ("运作方式", "视频", "Founding 50", "演示", "资料", "交易工作区", "证据清单", "托管指南", "x402 对比", "条款与风险", "隐私", "EN"),
}


def _localized_navigation(locale: str) -> str:
    how, videos, founding, demo, resources, workspace, evidence, escrow, x402, terms, privacy, english = map(escape, NAV[locale])
    return (f'<div class="landing-nav-row"><a href="/{locale}#how">{how}</a>'
            f'<a href="/{locale}#videos">{videos}</a>'
            f'<a href="/mainnet/founding50" data-event="founding_click">{founding} ({english})</a>'
            f'<a href="/play" data-event="demo_click">{demo} ({english})</a>'
            f'<details class="language-menu resource-menu"><summary>{resources}</summary><div>'
            f'<a href="/mainnet?lang={locale}">{workspace}</a>'
            f'<a href="/ai-agent-job-evidence">{evidence} ({english})</a>'
            f'<a href="/ai-agent-escrow">{escrow} ({english})</a>'
            f'<a href="/x402-vs-agent-escrow">{x402} ({english})</a>'
            f'<a href="/terms">{terms} ({english})</a>'
            f'<a href="/privacy">{privacy} ({english})</a></div></details></div>')


def _localized_footer(locale: str) -> str:
    _, _, _, _, _, _, evidence, escrow, x402, terms, privacy, english = map(escape, NAV[locale])
    return (f'<footer><div class="wrap"><a class="brand" href="/"><span class="brand-mark" aria-hidden="true"></span><span>AgentSolis Protocol</span></a>'
            f'<span><a href="/ai-agent-escrow">{escrow} ({english})</a> · '
            f'<a href="/x402-vs-agent-escrow">{x402} ({english})</a> · '
            f'<a href="/ai-agent-job-evidence">{evidence} ({english})</a> · '
            f'<a href="/terms">{terms} ({english})</a> · '
            f'<a href="/privacy">{privacy} ({english})</a> · '
            f'<a href="/.well-known/agent-card.json">Agent card ({english})</a></span></div></footer>')

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
    english_note = {"tr": "İngilizce", "es": "inglés", "pt-br": "inglês", "ru": "английский", "zh-cn": "英语"}[locale]
    steps = "".join(f'<article class="step"><b>0{i}</b><h3>{escape(title)}</h3><p>{escape(copy)}</p></article>' for i, (title, copy) in enumerate(data["steps"], 1))
    status_check, status_open, status_limited, status_closed, status_unknown = data["status"]
    canonical = f"https://agentsolis.solists.com.tr/{locale}"
    og_locale = {"tr": "tr_TR", "es": "es_ES", "pt-br": "pt_BR", "ru": "ru_RU", "zh-cn": "zh_CN"}[locale]
    social_image = "https://agentsolis.solists.com.tr/assets/agentsolis-social-card.png"
    schema = json.dumps({
        "@context": "https://schema.org", "@type": "WebPage", "name": data["title"],
        "description": data["lead"], "url": canonical, "inLanguage": data["lang"],
        "isPartOf": {"@type": "WebSite", "name": "AgentSolis", "url": "https://agentsolis.solists.com.tr/"},
    }, ensure_ascii=False).replace("<", "\\u003c")
    return f'''<!doctype html><html lang="{data["lang"]}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(data["title"])} — AgentSolis</title><meta name="description" content="{escape(data["lead"], quote=True)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{canonical}">{_alternate_links()}<link rel="icon" href="/favicon.ico">
<meta property="og:type" content="website"><meta property="og:site_name" content="AgentSolis"><meta property="og:locale" content="{og_locale}"><meta property="og:title" content="{escape(data["title"], quote=True)} — AgentSolis"><meta property="og:description" content="{escape(data["lead"], quote=True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{social_image}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{escape(data["title"], quote=True)} — AgentSolis"><meta name="twitter:description" content="{escape(data["lead"], quote=True)}"><meta name="twitter:image" content="{social_image}"><script type="application/ld+json">{schema}</script><link rel="stylesheet" href="/assets/brand.css?v=20261029trust"></head>
<body class="landing"><header class="hero localized-hero"><div class="wrap"><nav><a class="brand" href="/" aria-label="AgentSolis home"><span class="brand-mark" aria-hidden="true"></span><span>AgentSolis</span></a><div class="landing-nav-stack">{_localized_navigation(locale)}<div class="language-switcher" aria-label="Language">{_language_links(locale)}</div><a class="nav-guide" href="/mainnet?lang={locale}#guide" data-event="guide_click">{escape(data["guide"])} →</a></div></nav><div class="localized-copy"><p class="eyebrow">Arbitrum One · Native USDC · Non-custodial</p><h1>{escape(data["title"])}</h1><p class="lead">{escape(data["lead"])}</p><p class="hero-proof">{escape(data["future"])}</p><div class="notice localized-status"><strong data-live-mainnet-status data-open="{escape(status_open)}" data-limited="{escape(status_limited)}" data-closed="{escape(status_closed)}" data-unknown="{escape(status_unknown)}">{escape(status_check)}</strong><br>{escape(data["network"])}</div><a class="button" href="/mainnet?lang={locale}#guide">{escape(data["open"])} →</a> <a class="button secondary" href="/mainnet/founding50" data-event="founding_click">{escape(data["founding"])} ({escape(english_note)}) →</a></div></div></header>
{localized_main(locale, data, steps)}{_localized_footer(locale)}<script src="/assets/video-guide.js?v=20261028d" defer></script><script src="/assets/localized-status.js?v=20261029a" defer></script><script src="/assets/launch-analytics.js" defer></script></body></html>'''
