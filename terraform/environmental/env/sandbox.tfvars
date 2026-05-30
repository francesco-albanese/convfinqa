# AWS Configuration
region       = "eu-west-2"
account_id   = "645275603781"
account_name = "sandbox"

# Cognito
cognito_hosted_ui_prefix = "convfinqa-sandbox"

# Domain
app_domain = "convfinqa-sandbox.francescoalbanese.dev"

extra_cognito_callback_urls = ["http://localhost:5173/api/auth/callback"]
extra_cognito_logout_urls   = ["http://localhost:5173/"]

# Observability
langfuse_enabled = true

# LLM — requires the Gemini API key provisioned out-of-band (like the Langfuse
# keys) as a SecureString SSM parameter at /convfinqa/sandbox/gemini_api_key.
gemini_enabled = true
