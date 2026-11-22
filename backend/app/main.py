from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api.routes import health, agents, workflows, auth, research, video, creative, publishing, analytics, oauth, ideas, production, editor, visuals

Path(settings.media_storage_dir).mkdir(parents=True, exist_ok=True)
app = FastAPI(title=settings.app_name, version='0.8.0', description='AI-assisted social content production API')
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'], allow_headers=['Authorization','Content-Type'])
app.include_router(health.router, prefix='/api/v1')
app.include_router(agents.router, prefix='/api/v1')
app.include_router(workflows.router, prefix='/api/v1')
app.include_router(auth.router, prefix='/api/v1')
app.include_router(oauth.router, prefix='/api/v1')
app.include_router(research.router, prefix='/api/v1')
app.include_router(video.router, prefix='/api/v1')
app.include_router(creative.router, prefix='/api/v1')
app.include_router(publishing.router, prefix='/api/v1')
app.include_router(analytics.router, prefix='/api/v1')
app.include_router(ideas.router, prefix='/api/v1')
app.include_router(production.router, prefix='/api/v1')
app.include_router(editor.router, prefix='/api/v1')
app.include_router(visuals.router, prefix='/api/v1')
app.mount('/media', StaticFiles(directory=settings.media_storage_dir), name='media')
