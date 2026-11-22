from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_name: str = 'BioinfoBeats AI Studio API'
    environment: str = 'development'
    database_url: str = 'postgresql+psycopg://bioinfobeats:local-dev-only@localhost:5432/bioinfobeats'
    redis_url: str = 'redis://localhost:6379/0'
    secret_key: str = 'unsafe-development-key-change-me'
    access_token_expire_minutes: int = 60
    cors_origins: str = 'http://localhost:3000'
    analytics_collection_hour_utc: int = 3
    llm_api_key: str = ''
    llm_base_url: str = 'https://api.openai.com/v1'
    llm_model: str = 'gpt-4o-mini'
    llm_timeout_seconds: int = 120
    tavily_api_key: str = ''
    youtube_api_key: str = ''
    google_oauth_client_id: str = ''
    google_oauth_client_secret: str = ''
    google_oauth_redirect_uri: str = 'http://localhost:8000/api/v1/oauth/google/callback'
    google_oauth_frontend_url: str = 'http://localhost:3000'
    oauth_token_encryption_key: str = ''
    research_timeout_seconds: int = 30
    elevenlabs_api_key: str = ''
    elevenlabs_voice_id: str = ''
    elevenlabs_model_id: str = 'eleven_multilingual_v2'
    openai_api_key: str = ''
    openai_base_url: str = 'https://api.openai.com/v1'
    openai_image_model: str = 'gpt-image-2'
    replicate_api_token: str = ''
    replicate_video_model_version: str = ''
    motion_generation_timeout_seconds: int = 900
    motion_poll_interval_seconds: int = 4
    render_timeout_seconds: int = 180
    media_storage_dir: str = '/data/media'
    ffmpeg_binary: str = 'ffmpeg'
    buffer_access_token: str = ''
    buffer_api_base_url: str = 'https://api.buffer.com'
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]
settings = Settings()
