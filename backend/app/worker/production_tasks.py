from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.workflow import Workflow
from app.rendering.service import render_video
from app.creative.service import create_creative_package

@celery_app.task(name="app.worker.production_tasks.assemble_approved_production", bind=True, max_retries=0)
def assemble_approved_production(self, workflow_id: str, render_id: str):
    db=SessionLocal()
    try:
        item=db.get(Workflow,workflow_id)
        if item is None: return {"status":"not_found"}
        config=item.config or {}
        job=config.get("production_assembly") or {}
        if job.get("render_id") != render_id: return {"status":"superseded"}
        script=config.get("approved_script") or ""
        title=config.get("approved_title") or item.topic
        if len(script.strip()) < 30:
            job={**job,"status":"failed","error":"Approved script is missing or too short."}
            item.config={**config,"production_assembly":job};db.commit()
            return {"status":"failed","error":job["error"]}
        job={**job,"status":"rendering","step":"narration_and_video"}
        item.config={**config,"production_assembly":job,"video_render":{"id":render_id,"status":"rendering","title":title,"aspect":job["aspect"]}}
        db.commit()
        try:
            video_url=render_video(render_id,title,script,job["aspect"],None,None,job.get("visual_mode","auto"))
            item=db.get(Workflow,workflow_id); config=item.config or {}
            item.config={**config,"video_render":{"id":render_id,"status":"ready_for_review","title":title,"aspect":job["aspect"],"storyboard":"auto","url":video_url}}
            item.config={**item.config,"production_assembly":{**job,"status":"generating_creatives","step":"thumbnails_and_social_copy","video_url":video_url}}
            db.commit()
            creative=create_creative_package(workflow_id,item.topic,title,script,["YouTube","Instagram","LinkedIn"])
            item=db.get(Workflow,workflow_id); config=item.config or {}
            item.config={**config,"creative_package":creative,"production_assembly":{**job,"status":"ready_for_review","step":"complete","video_url":video_url}}
            db.commit()
            return {"workflow_id":workflow_id,"status":"ready_for_review","video_url":video_url}
        except Exception as exc:
            item=db.get(Workflow,workflow_id); config=item.config or {}
            prior=config.get("production_assembly") or job
            item.config={**config,"production_assembly":{**prior,"status":"failed","error":str(exc)[:1000]}}
            db.commit()
            raise
    finally:
        db.close()
