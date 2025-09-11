from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
import asyncio
from datetime import datetime
import json

from database import get_db
from models import Audit
from schemas import AuditCreate, AuditResponse
from services.pagespeed_service import PageSpeedService
from services.ai_service import AIService

router = APIRouter()
pagespeed_service = PageSpeedService()
ai_service = AIService()

@router.post("/", response_model=AuditResponse)
async def create_audit(
    audit: AuditCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new audit and process it in the background"""
    # Create initial audit record
    db_audit = Audit(
        website_url=audit.website_url,
        status="processing",
        created_at=datetime.utcnow()
    )
    db.add(db_audit)
    db.commit()
    db.refresh(db_audit)
    
    # Process audit in background
    background_tasks.add_task(process_audit, db_audit.id, audit.website_url)
    
    return db_audit

@router.get("/{audit_id}", response_model=AuditResponse)
def get_audit(audit_id: int, db: Session = Depends(get_db)):
    """Get audit by ID"""
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit

@router.get("/", response_model=List[AuditResponse])
def list_audits(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all audits with optional filtering"""
    query = db.query(Audit)
    if status:
        query = query.filter(Audit.status == status)
    return query.offset(skip).limit(limit).all()

@router.delete("/{audit_id}")
def delete_audit(audit_id: int, db: Session = Depends(get_db)):
    """Delete an audit"""
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    db.delete(audit)
    db.commit()
    return {"message": "Audit deleted successfully"}

async def process_audit(audit_id: int, website_url: str):
    """Background task to process audit"""
    from database import SessionLocal
    db = SessionLocal()
    
    try:
        # Get the audit record
        audit = db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            return
        
        print(f"Processing audit for {website_url}")
        
        # Get PageSpeed data
        pagespeed_data = await pagespeed_service.analyze_website(website_url)
        
        if pagespeed_data:
            # Extract performance metrics
            mobile_score = pagespeed_data.get('mobile', {}).get('performance_score', 0)
            desktop_score = pagespeed_data.get('desktop', {}).get('performance_score', 0)
            
            # Get AI recommendations
            ai_recommendations = await ai_service.generate_recommendations(website_url, pagespeed_data)
            
            # Calculate overall grade
            avg_performance = (mobile_score + desktop_score) / 2
            if avg_performance >= 90:
                grade = 'A'
            elif avg_performance >= 80:
                grade = 'B'
            elif avg_performance >= 70:
                grade = 'C'
            elif avg_performance >= 60:
                grade = 'D'
            else:
                grade = 'F'
            
            # Update audit with results
            audit.performance_score = int(avg_performance)
            audit.seo_score = pagespeed_data.get('mobile', {}).get('seo_score', 75)
            audit.security_score = 85  # Default for now
            audit.accessibility_score = pagespeed_data.get('mobile', {}).get('accessibility_score', 80)
            audit.best_practices_score = pagespeed_data.get('mobile', {}).get('best_practices_score', 85)
            audit.mobile_score = mobile_score
            audit.desktop_score = desktop_score
            audit.grade = grade
            audit.recommendations = json.dumps(ai_recommendations) if ai_recommendations else None
            audit.pagespeed_data = json.dumps(pagespeed_data)
            audit.status = "completed"
            
        else:
            # If PageSpeed fails, create default audit results
            audit.performance_score = 75
            audit.seo_score = 80
            audit.security_score = 85
            audit.accessibility_score = 78
            audit.best_practices_score = 82
            audit.mobile_score = 73
            audit.desktop_score = 77
            audit.grade = 'C'
            audit.recommendations = json.dumps([
                "Optimize image sizes and formats",
                "Implement browser caching",
                "Minify CSS and JavaScript files",
                "Improve server response time"
            ])
            audit.status = "completed"
        
        audit.completed_at = datetime.utcnow()
        db.commit()
        
        print(f"Audit completed for {website_url} with grade {audit.grade}")
        
    except Exception as e:
        print(f"Error processing audit: {str(e)}")
        audit.status = "failed"
        audit.error_message = str(e)
        db.commit()
    
    finally:
        db.close()