from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import health,agents,workflows
app=FastAPI(title=settings.app_name,version='0.1.0',description='AI-assisted social content production API')
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_credentials=True,allow_methods=['GET','POST','OPTIONS'],allow_headers=['Authorization','Content-Type'])
app.include_router(health.router,prefix='/api/v1');app.include_router(agents.router,prefix='/api/v1');app.include_router(workflows.router,prefix='/api/v1')
