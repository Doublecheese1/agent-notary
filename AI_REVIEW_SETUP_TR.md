# AgentSolis uyuşmazlık ajanlarını canlı çalıştırma

Kod üç ayrı servis türünü destekler ve bütün servislerden katı JSON karar çıktısı ister:

1. OpenAI Responses API: `https://api.openai.com/v1/responses`
2. xAI Chat Completions API: `https://api.x.ai/v1/chat/completions`
3. Anthropic Messages API: `https://api.anthropic.com/v1/messages`

ChatGPT Pro aboneliği OpenAI API anahtarı sağlamaz. Her servis için ilgili geliştirici hesabından ayrı API anahtarı ve kullanılacak model adı gerekir. Anahtarlar yalnız barındırma hizmetinin gizli ortam değişkenlerine yazılır; Git deposuna, tarayıcıya veya sözleşmeye yazılmaz.

## Zorunlu canlı ayarlar

- `AI_REVIEW_PROVIDER_A/B/C_URL`, `MODEL`, `API_KEY`, `STYLE`
- En az 32 karakterli `AI_REVIEW_TRIGGER_TOKEN`
- Kanıtların alınabileceği açık alan adları: `AI_REVIEW_ALLOWED_EVIDENCE_HOSTS`
- Zincire otomatik karar göndermek için üç ayrı KMS/HSM imzacı servisi
- Aynı işlemi ikinci kez göndermeyen bir relayer ve relayer adresi
- Kalıcı `AI_REVIEW_DB_PATH`

Üç sağlayıcı aynı internet alan adını kullanırsa hazır olma kontrolü başarısız olur. Otomatik zincir işlemi açılırsa üç imzacı URL'sinin de birbirinden ayrı olması ve relayer'ın eksiksiz yapılandırılması gerekir.

## Güvenli açılış sırası

1. Anahtarları ve model adlarını sunucu sırlarına girin.
2. `AI_REVIEW_ENABLED=true`, `AI_REVIEW_AUTOMATIC_EXECUTION=false` ile yalnız değerlendirmeyi açın.
3. `GET /internal/ai-review/readiness` çağrısında `evaluation_ready=true` görünmesini doğrulayın.
4. Sentetik bir uyuşmazlıkla üç sağlayıcının ayrı cevap verdiğini ve 2/3 sonucunun doğru üretildiğini doğrulayın.
5. Üç izole imzacı ve relayer denendikten sonra `AI_REVIEW_AUTOMATIC_EXECUTION=true` yapın; `execution_ready=true` olmadan zincir işlemi başlatılmaz.

Resmî biçimler: [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses), [xAI Structured Outputs](https://docs.x.ai/developers/model-capabilities/text/structured-outputs), [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).

