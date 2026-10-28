"""Send the five newly researched AgentSolis outreach drafts from Render Web Shell.
Uses Render Secret SMTP/CRM variables; dedupes before sending and records evidence."""
import os, smtplib, sqlite3, time
from email.message import EmailMessage
from email.utils import make_msgid

SENDER = "agentsolis@solists.com.tr"
SITE = "https://agentsolis.solists.com.tr/"
FOUNDING = SITE + "mainnet/founding50"

TARGETS = [
    ("AI Automation Agency", "info@aiautomationagency.ca", "en", "the way you build practical AI automation solutions for businesses", "one small automation project with a clear business result, delivery checklist and evidence"),
    ("The Automators", "info@theautomators.ai", "en", "your work with custom automation, voice agents and measurable business outcomes", "one small voice-agent or workflow project with a clear scope, delivery checklist and acceptance result"),
    ("Core Labs", "contato@corelabs.com.br", "pt", "your Claude agents, n8n workflows and API integrations for Mercado Livre and other systems", "one small Mercado Livre workflow with a clear result, evidence checklist and acceptance step"),
    ("OneIA", "contato@oneiasolucoes.com.br", "pt", "your B2B prospecting with AI agents over the official WhatsApp API", "one small prospecting campaign with a clear result such as qualified leads or booked meetings"),
    ("fazer.ai", "contato@fazer.ai", "pt", "your on-premise agents and open models such as Qwen and DeepSeek", "one small on-premise agent installation or workflow with clear evidence and acceptance criteria"),
]

def english(company, detail, example):
    return f'''Greetings from Istanbul,

I'm Yigit from Solis Trade Solutions.

I spent some time looking at {company}, especially {detail}. That made me think there might be a very natural way to try our systems together.

Our product is AgentSolis, an escrow and settlement service for online work between people, AI agents, or both. The buyer and seller agree on the result, evidence and acceptance steps first. The budget is then held in escrow and released after the agreed delivery is accepted.

For example, {example}. AgentSolis could hold the agreed budget while the work is being done and release it after the delivery is accepted.

I think there is a real opportunity for us to work together here. We could try one small real {company} job through our escrow and see whether the two systems work naturally side by side. To achieve that, we can use our new Founding 50 section, which we opened after the feedback we received from our first customers. For the first 50 approved buyer or seller participant wallets, there will be no AgentSolis protocol fee for 30 days from that participant's first funded deal. We could use it to run a small trial together.

You can try the system here:

{SITE}

Founding 50:

{FOUNDING}

Come and try one small real {company} job with us. If anything is unclear, please tell me and I will show you personally. The website also explains the flow step by step.

Maybe we can try one example together and see what comes out of it. We look forward to hearing from you.

Yigit Guler
Solis Trade Solutions
AgentSolis
'''

def portuguese(company, detail, example):
    return f'''Olá, tudo bem?

Eu sou Yigit, da Solis Trade Solutions.

Passei algum tempo conhecendo a {company}, especialmente {detail}. Isso me fez pensar que pode existir uma forma muito natural de testar os nossos sistemas juntos.

O nosso produto é a AgentSolis, um serviço de escrow e settlement para trabalhos online entre pessoas, agentes de IA ou os dois. O comprador e o vendedor definem primeiro o resultado, as evidências e as etapas de aceitação. Depois, o orçamento fica protegido em escrow e é liberado quando a entrega combinada é aceita.

Por exemplo, poderíamos testar {example}. A AgentSolis manteria o orçamento protegido durante o trabalho e liberaria o pagamento depois da aceitação da entrega.

Acho que existe uma oportunidade real para trabalharmos juntos. Podemos experimentar um pequeno projeto real da {company} através da nossa escrow e ver se os dois sistemas funcionam naturalmente lado a lado. Para fazer isso, podemos usar a nova seção Founding 50, que abrimos depois do feedback que recebemos dos nossos primeiros clientes. Para as primeiras 50 carteiras de participantes aprovadas, sejam compradores ou vendedores, não haverá taxa de protocolo da AgentSolis durante 30 dias a partir do primeiro negócio financiado daquele participante. Podemos usar essa oportunidade para fazer um pequeno teste juntos.

Você pode experimentar o sistema aqui:

{SITE}

Founding 50:

{FOUNDING}

Venha experimentar um pequeno projeto real da {company} conosco. Se alguma coisa não ficar clara, me avise e eu mostro pessoalmente. O site também explica o processo passo a passo.

Talvez possamos testar um exemplo juntos e ver o que acontece. Ficarei feliz em ouvir vocês.

Yigit Guler
Solis Trade Solutions
AgentSolis
'''

db_path = os.getenv("OUTREACH_CRM_DB_PATH", "/var/data/agentnotary/outreach-crm.sqlite3")
db = sqlite3.connect(db_path)
now = int(time.time())
host = os.environ["REPORT_SMTP_HOST"]
port = int(os.environ["REPORT_SMTP_PORT"])
user = os.environ.get("REPORT_SMTP_USER") or os.environ["REPORT_SMTP_USERNAME"]
password = os.environ["REPORT_SMTP_APP_PASSWORD"]
smtp_cls = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP

sent = 0
with smtp_cls(host, port, timeout=30) as smtp:
    if port != 465:
        smtp.starttls()
    smtp.login(user, password)
    for company, recipient, language, detail, example in TARGETS:
        lead = db.execute("SELECT id,status FROM outreach_leads WHERE lower(channel_value)=lower(?) LIMIT 1", (recipient,)).fetchone()
        if lead and lead[1] in ("sent", "replied", "positive", "demo", "founding50", "escrow", "won", "bounced", "opt_out"):
            print("SKIP_ALREADY_CONTACTED", company, recipient)
            continue
        lead_id = lead[0] if lead else f"L-20261027-new5-{sent+1:02d}"
        subject = f"A small real {company} job through AgentSolis" if language == "en" else f"Um pequeno projeto real da {company} com a AgentSolis"
        body = english(company, detail, example) if language == "en" else portuguese(company, detail, example)
        if not lead:
            db.execute("INSERT INTO outreach_leads (id,company_name,website,country,country_verified,channel_type,channel_value,source_url,segment,owner,status,subject,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (lead_id, company, "", "Canada" if language == "en" else "Brazil", 1, "email", recipient, "", "agent_builder", "codex", "draft", subject, now, now))
        msg = EmailMessage()
        msg["From"] = SENDER; msg["To"] = recipient; msg["Cc"] = SENDER; msg["Reply-To"] = SENDER; msg["Subject"] = subject; msg["Message-ID"] = make_msgid(domain="solists.com.tr")
        msg.set_content(body)
        refused = smtp.send_message(msg)
        if refused:
            print("REFUSED", company, sorted(refused)); continue
        mid = msg["Message-ID"]
        summary = "Approved warm product-specific Founding 50 invitation; SMTP accepted; CC to sender."
        db.execute("INSERT INTO outreach_events (lead_id,kind,occurred_at,subject,message_summary,source_url,created_at) VALUES (?,?,?,?,?,?,?)", (lead_id, "sent", now, subject, summary, "smtp_accept:" + mid, now))
        db.execute("INSERT OR IGNORE INTO outreach_messages (message_id,mailbox,direction,sender,recipients,cc,subject,occurred_at,status,body_summary,lead_id,synced_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (mid, "Sent", "outbound", SENDER, recipient, SENDER, subject, now, "sent", summary, lead_id, now))
        db.execute("UPDATE outreach_leads SET status='sent',first_contact_at=COALESCE(first_contact_at,?),last_contact_at=?,updated_at=? WHERE id=?", (now, now, now, lead_id))
        db.commit()
        sent += 1
        print("SENT", company, recipient, mid)
print("TOTAL_SENT=" + str(sent))
