"""Build timed captions for the five illustrative AgentSolis videos.

Times come from the 28 October 2026 transcription of the actual MP4 audio.
Brand/product words have been corrected from speech recognition output.
"""

from pathlib import Path


TIMES = {
    "01": [(10.32, 16.62), (16.62, 19.92), (19.92, 22.42), (22.42, 26.62)],
    "02": [(0.18, 11.43), (11.43, 15.31), (15.31, 21.02), (21.02, 23.14), (23.14, 25.62), (25.62, 28.66)],
    "03": [(7.34, 13.34), (13.34, 15.34), (15.34, 20.62), (20.62, 23.62), (24.62, 27.62)],
    "04": [(2.64, 9.64), (9.64, 22.40), (22.40, 27.40)],
    "05": [(3.22, 5.22), (5.74, 11.78), (12.22, 17.30), (17.86, 20.38), (21.38, 24.82)],
}


CAPTIONS = {
    "en": {
        "01": [
            "Before an online job begins, the buyer and seller agree on the result, evidence, deadline, and price.",
            "The buyer locks the agreed USDC budget in escrow.",
            "The seller delivers the work with evidence.",
            "The buyer then accepts the delivery or follows the agreed dispute process.",
        ],
        "02": [
            "To get started, connect the wallet you'll use for your deal.",
            "Open AgentSolis and select your wallet.",
            "Check that you're on Arbitrum One and that the address is yours.",
            "Connecting lets you inspect the next step.",
            "It does not move USDC.",
            "Approval and funding are separate actions you choose later.",
        ],
        "03": [
            "As the buyer, you agree on the result, the evidence, and the budget first.",
            "Review the terms together.",
            "When you're ready, approve USDC.",
            "Then lock the agreed budget in escrow.",
            "The seller can now work towards the agreed result.",
        ],
        "04": [
            "The seller opens the invitation and checks the result, deadline, and evidence the buyer expects.",
            "After accepting the seller role, they complete the job and submit the agreed work and evidence.",
            "The buyer then reviews the delivery and can accept it or raise a dispute.",
        ],
        "05": [
            "Want to try one real job together?",
            "Founding 50 is open to the first 50 approved participant wallets, whether you're a buyer, a seller, or both.",
            "From that wallet's first funded deal, there is no AgentSolis protocol fee for 30 days.",
            "The job amount and network costs still apply.",
            "Apply with your wallet, and let's try one small job.",
        ],
    },
    "tr": {
        "01": [
            "Çevrimiçi bir iş başlamadan önce alıcı ve satıcı sonuç, kanıt, süre ve fiyat üzerinde anlaşır.",
            "Alıcı, kararlaştırılan USDC bütçesini emanet sözleşmede kilitler.",
            "Satıcı işi kanıtıyla birlikte teslim eder.",
            "Alıcı teslimatı kabul eder ya da kararlaştırılan uyuşmazlık sürecini izler.",
        ],
        "02": [
            "Başlamak için işlemde kullanacağınız cüzdanı bağlayın.",
            "AgentSolis'i açıp cüzdanınızı seçin.",
            "Arbitrum One ağında olduğunuzu ve adresin size ait olduğunu kontrol edin.",
            "Cüzdanı bağlamak sonraki adımı görmenizi sağlar.",
            "Bu işlem USDC taşımaz.",
            "USDC onayı ve fonlama, daha sonra sizin seçeceğiniz ayrı işlemlerdir.",
        ],
        "03": [
            "Alıcı olarak önce sonuç, kanıt ve bütçe üzerinde anlaşırsınız.",
            "Şartları birlikte gözden geçirin.",
            "Hazır olduğunuzda USDC kullanımına onay verin.",
            "Ardından kararlaştırılan bütçeyi emanet sözleşmede kilitleyin.",
            "Satıcı artık kararlaştırılan sonuç için çalışabilir.",
        ],
        "04": [
            "Satıcı daveti açar; alıcının beklediği sonucu, süreyi ve kanıtı inceler.",
            "Satıcı rolünü kabul ettikten sonra işi tamamlar, kararlaştırılan işi ve kanıtı teslim eder.",
            "Alıcı teslimatı inceler; kabul edebilir veya uyuşmazlık başlatabilir.",
        ],
        "05": [
            "Birlikte gerçek bir küçük iş denemek ister misiniz?",
            "Founding 50, alıcı, satıcı veya her iki roldeki ilk 50 onaylı katılımcı cüzdanına açıktır.",
            "Cüzdanın ilk fonlanan işleminden itibaren 30 gün AgentSolis protokol ücreti yoktur.",
            "İş bedeli ve ağ masrafları geçerliliğini korur.",
            "Cüzdanınızla başvurun; birlikte küçük bir iş deneyelim.",
        ],
    },
    "es": {
        "01": [
            "Antes de empezar un trabajo en línea, comprador y vendedor acuerdan el resultado, las pruebas, el plazo y el precio.",
            "El comprador bloquea en escrow el presupuesto acordado en USDC.",
            "El vendedor entrega el trabajo con pruebas.",
            "Después, el comprador acepta la entrega o sigue el proceso de disputa acordado.",
        ],
        "02": [
            "Para empezar, conecta la billetera que usarás en la operación.",
            "Abre AgentSolis y selecciona tu billetera.",
            "Comprueba que estás en Arbitrum One y que la dirección es tuya.",
            "Conectarla te permite ver el siguiente paso.",
            "Esto no mueve USDC.",
            "La aprobación y la financiación son acciones separadas que eliges más adelante.",
        ],
        "03": [
            "Como comprador, primero acuerdas el resultado, las pruebas y el presupuesto.",
            "Revisad juntos las condiciones.",
            "Cuando estés listo, aprueba el uso de USDC.",
            "Después, bloquea en escrow el presupuesto acordado.",
            "El vendedor ya puede trabajar para lograr el resultado acordado.",
        ],
        "04": [
            "El vendedor abre la invitación y revisa el resultado, el plazo y las pruebas que espera el comprador.",
            "Tras aceptar su papel, realiza el trabajo y entrega el resultado y las pruebas acordadas.",
            "El comprador revisa la entrega y puede aceptarla o abrir una disputa.",
        ],
        "05": [
            "¿Probamos juntos un trabajo real y pequeño?",
            "Founding 50 está abierto a las primeras 50 billeteras participantes aprobadas, sean de comprador, vendedor o ambos.",
            "Desde la primera operación financiada de esa billetera, no hay comisión de protocolo de AgentSolis durante 30 días.",
            "El precio del trabajo y los costes de red siguen aplicándose.",
            "Solicítalo con tu billetera y probemos juntos un pequeño trabajo.",
        ],
    },
    "pt-br": {
        "01": [
            "Antes de começar um trabalho on-line, comprador e vendedor combinam o resultado, as evidências, o prazo e o preço.",
            "O comprador bloqueia em escrow o orçamento combinado em USDC.",
            "O vendedor entrega o trabalho com evidências.",
            "Depois, o comprador aceita a entrega ou segue o processo de disputa combinado.",
        ],
        "02": [
            "Para começar, conecte a carteira que você usará na transação.",
            "Abra o AgentSolis e selecione sua carteira.",
            "Confira se está na Arbitrum One e se o endereço é seu.",
            "A conexão permite ver a próxima etapa.",
            "Ela não movimenta USDC.",
            "A aprovação e o depósito são ações separadas, escolhidas depois por você.",
        ],
        "03": [
            "Como comprador, primeiro você combina o resultado, as evidências e o orçamento.",
            "Revisem juntos as condições.",
            "Quando estiver pronto, aprove o uso de USDC.",
            "Depois, bloqueie em escrow o orçamento combinado.",
            "O vendedor já pode trabalhar para alcançar o resultado combinado.",
        ],
        "04": [
            "O vendedor abre o convite e confere o resultado, o prazo e as evidências esperadas pelo comprador.",
            "Após aceitar o papel de vendedor, conclui o trabalho e envia a entrega e as evidências combinadas.",
            "O comprador revisa a entrega e pode aceitá-la ou abrir uma disputa.",
        ],
        "05": [
            "Vamos experimentar juntos um pequeno trabalho real?",
            "O Founding 50 está aberto às primeiras 50 carteiras participantes aprovadas, de compradores, vendedores ou ambos.",
            "A partir do primeiro negócio financiado dessa carteira, não há taxa de protocolo da AgentSolis por 30 dias.",
            "O valor do trabalho e os custos de rede continuam valendo.",
            "Inscreva-se com sua carteira e vamos testar um pequeno trabalho.",
        ],
    },
    "ru": {
        "01": [
            "До начала онлайн-заказа покупатель и продавец согласуют результат, доказательства, срок и цену.",
            "Покупатель блокирует согласованный бюджет в USDC в эскроу.",
            "Продавец передаёт работу с доказательствами.",
            "Затем покупатель принимает результат или следует согласованной процедуре спора.",
        ],
        "02": [
            "Для начала подключите кошелёк, который будете использовать в сделке.",
            "Откройте AgentSolis и выберите свой кошелёк.",
            "Убедитесь, что выбрана сеть Arbitrum One и адрес принадлежит вам.",
            "Подключение позволяет увидеть следующий шаг.",
            "Оно не переводит USDC.",
            "Одобрение USDC и внесение средств — отдельные действия, которые вы выбираете позже.",
        ],
        "03": [
            "Как покупатель, сначала согласуйте результат, доказательства и бюджет.",
            "Вместе проверьте условия.",
            "Когда будете готовы, одобрите использование USDC.",
            "Затем заблокируйте согласованный бюджет в эскроу.",
            "Теперь продавец может работать над согласованным результатом.",
        ],
        "04": [
            "Продавец открывает приглашение и проверяет результат, срок и доказательства, ожидаемые покупателем.",
            "Приняв роль продавца, он выполняет заказ и передаёт согласованную работу с доказательствами.",
            "Покупатель проверяет результат и может принять его или открыть спор.",
        ],
        "05": [
            "Хотите вместе попробовать один небольшой реальный заказ?",
            "Founding 50 доступна первым 50 одобренным кошелькам участников: покупателей, продавцов или обеих ролей.",
            "С первой профинансированной сделки этого кошелька 30 дней не взимается протокольная комиссия AgentSolis.",
            "Стоимость работы и сетевые расходы при этом сохраняются.",
            "Подайте заявку со своим кошельком, и давайте попробуем небольшой заказ.",
        ],
    },
    "zh-cn": {
        "01": [
            "在线工作开始前，买卖双方先约定成果、交付证据、期限和价格。",
            "买方将约定的 USDC 预算锁定在托管合约中。",
            "卖方提交工作成果及证据。",
            "随后买方接受交付，或按约定的争议流程处理。",
        ],
        "02": [
            "开始前，请连接本次交易要使用的钱包。",
            "打开 AgentSolis 并选择你的钱包。",
            "确认网络为 Arbitrum One，且钱包地址属于你。",
            "连接钱包后，你可以查看下一步。",
            "仅连接钱包不会转移 USDC。",
            "授权使用 USDC 和实际存入资金是之后由你选择的两个独立操作。",
        ],
        "03": [
            "作为买方，先约定成果、证据和预算。",
            "双方共同核对条款。",
            "准备好后，授权使用 USDC。",
            "然后将约定的预算锁定在托管合约中。",
            "卖方现在可以着手完成约定的成果。",
        ],
        "04": [
            "卖方打开邀请，核对买方要求的成果、期限和证据。",
            "接受卖方角色后，完成工作并提交约定的成果和证据。",
            "买方随后审核交付，可以接受，也可以发起争议。",
        ],
        "05": [
            "想一起试做一笔真实的小额工作吗？",
            "Founding 50 面向首批 50 个获批的参与者钱包，买方、卖方或兼具两种角色均可申请。",
            "从该钱包首次完成资金锁定的交易起，30 天内免收 AgentSolis 协议费。",
            "工作款项和网络费用仍需支付。",
            "使用钱包申请，让我们一起试做一笔小工作。",
        ],
    },
}


def timestamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1_000)
    return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"


def build() -> None:
    target = Path(__file__).resolve().parents[1] / "static" / "videos"
    for lang, videos in CAPTIONS.items():
        for chapter, cues in videos.items():
            timings = TIMES[chapter]
            assert len(cues) == len(timings), (lang, chapter)
            lines = ["WEBVTT", ""]
            for (start, end), caption in zip(timings, cues):
                assert 0 <= start < end <= 30.08
                lines.extend([f"{timestamp(start)} --> {timestamp(end)}", caption, ""])
            (target / f"{chapter}.{lang}.vtt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    build()
