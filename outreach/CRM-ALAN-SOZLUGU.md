# AgentSolis CRM alan sözlüğü

## `crm-leads.csv`

| Alan | Tanım |
|---|---|
| `lead_id` | Değişmeyen benzersiz lead kodu. |
| `created_at` | İlk kayıt zamanı, ISO 8601 ve Europe/Istanbul. |
| `updated_at` | Son değişiklik zamanı. |
| `company_or_person` | Doğrulanmış şirket veya kamuya açık profesyonel kişi adı. |
| `lead_type` | `company` veya `individual`. |
| `segment` | Playbook'taki izin verilen segment. |
| `country` | Doğrulanmış ülke; bilinmiyorsa `unknown`. |
| `country_source_url` | Ülke bilgisini doğrulayan kaynak. |
| `website_or_profile_url` | Resmî site veya profesyonel profil. |
| `need_summary` | Güncel ihtiyacın tarafsız kısa özeti. |
| `need_source_url` | İhtiyacı kanıtlayan güncel bağlantı. |
| `need_source_date` | Kaynağın tarihi; bilinmiyorsa boş. |
| `contact_channel` | E-posta, form veya platform. |
| `contact_address_or_url` | Doğrulanmış e-posta ya da iletişim URL'si. |
| `contact_source_url` | Kanalın resmî olduğunu doğrulayan kaynak. |
| `status` | Playbook'taki lead durumu. |
| `priority` | `hot`, `strong`, `medium`, `low`. |
| `owner_agent` | Kaydı yöneten ajan. |
| `last_contact_at` | Son gerçek temas zamanı. |
| `next_action` | Sonraki somut görev. |
| `next_action_at` | Görevin zamanı. |
| `follow_up_count` | Gönderilmiş takip sayısı; en fazla 1. |
| `do_not_contact` | `true` veya `false`. |
| `stop_reason` | Opt-out, ret, hard bounce veya spam gibi durdurma nedeni. |
| `notes` | Kısa, doğrulanmış ek bilgi. |

## `crm-interactions.csv`

| Alan | Tanım |
|---|---|
| `interaction_id` | Benzersiz olay kodu. |
| `lead_id` | Ana lead kaydına bağlantı. |
| `occurred_at` | Olay zamanı. |
| `direction` | `outbound`, `inbound` veya `system`. |
| `channel` | Kullanılan iletişim kanalı. |
| `event_type` | `sent`, `delivered`, `soft_bounce`, `hard_bounce`, `spam_warning`, `reply`, `follow_up_sent`, `meeting_booked`. |
| `from_address` | Gönderici adresi; e-postada AgentSolis adresi. |
| `to_address_or_url` | Gerçek hedef adres/kanal. |
| `cc_address` | E-postada `agentsolis@solists.com.tr`. |
| `subject_or_context` | E-posta konusu veya platform konuşma başlığı. |
| `message_template_id` | Kullanılan taslak/sürüm kimliği. |
| `provider_message_id` | Posta/platform sağlayıcısının olay kimliği; varsa. |
| `reply_class` | Playbook'taki cevap sınıfı. |
| `reply_summary` | Anlamı bozmayan kısa cevap özeti. |
| `evidence_url_or_ref` | Olayı doğrulayan güvenli kayıt/başvuru. |
| `recorded_by` | Kaydı ekleyen ajan. |

## `crm-conversions.csv`

| Alan | Tanım |
|---|---|
| `conversion_id` | Benzersiz dönüşüm kodu. |
| `lead_id` | Lead ile doğrulanmış bağlantı varsa kod; yoksa boş. |
| `occurred_at` | Dönüşüm zamanı. |
| `conversion_type` | `demo`, `founding50`, `wallet_connected`, `escrow_created`, `escrow_funded`, `escrow_closed`, `protocol_revenue`. |
| `wallet_address` | Doğrulanmış açık cüzdan adresi; varsa. |
| `counterparty_wallet` | Doğrulanmış diğer taraf; varsa. |
| `deal_id` | Zincir üstü deal kimliği; varsa. |
| `tx_hash` | Zincir üstü işlem hash'i; varsa. |
| `amount_usdc` | İlgili escrow/fonlama tutarı. |
| `protocol_revenue_usdc` | Kesinleşmiş AgentSolis geliri; escrow bakiyesi değildir. |
| `country` | Yalnız doğrulanmış ülke; yoksa `unknown`. |
| `source_system` | `analytics`, `app`, `crm`, `arbitrum` veya diğer doğrulanmış sistem. |
| `evidence_url_or_ref` | Doğrulama kaydı. |
| `recorded_by` | Kaydı ekleyen ajan. |

