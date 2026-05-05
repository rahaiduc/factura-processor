from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # xAI
    xai_api_key: str
    ai_model: str = "grok-3-latest"

    # Google OAuth
    google_credentials_file: str = "credentials/credentials.json"
    google_token_file: str = "credentials/token.json"

    # Gmail
    gmail_query: str = "has:attachment filename:pdf is:unread"
    processed_label: str = "factura-procesada"

    # Google Sheets
    spreadsheet_id: str
    sheet_name: str = "Facturas"

    # App
    log_level: str = "INFO"
