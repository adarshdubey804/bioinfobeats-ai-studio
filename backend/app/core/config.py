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
    llm_api_key: str = ''
    llm_base_url: str = 'https://api.openai.com/v1'
    llm_model: str = 'gpt-4o-mini'
    llm_timeout_seconds: int = 120
    tavily_api_key: str = ''
    youtube_api_key: str = ''
    research_timeout_seconds: int = 30
    elevenlabs_api_key: str = ''
    elevenlabs_voice_id: str = ''
    elevenlabs_model_id: str = 'eleven_multilingual_v2'
    render_timeout_seconds: int = 180
    media_storage_dir: str = '/data/media'
    ffmpeg_binary: str = 'ffmpeg'
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]
settings = Settings()
