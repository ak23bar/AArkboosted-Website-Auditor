from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import json
from datetime import datetime
import asyncio
import httpx

app = FastAPI(title="AArkboosted Audit Tool")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class AuditCreate(BaseModel):
    website_url: str

class AuditResponse(BaseModel):
    id: int
    website_url: str
    status: str
    grade: Optional[str] = None
    performance_score: Optional[int] = None
    seo_score: Optional[int] = None
    security_score: Optional[int] = None
    accessibility_score: Optional[int] = None
    best_practices_score: Optional[int] = None
    mobile_score: Optional[int] = None
    desktop_score: Optional[int] = None
    recommendations: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class LoginRequest(BaseModel):
    username: str
    password: str

# Database setup
def init_db():
    conn = sqlite3.connect('arkboosted_audits.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            website_url TEXT NOT NULL,
            status TEXT DEFAULT 'processing',
            grade TEXT,
            performance_score INTEGER,
            seo_score INTEGER,
            security_score INTEGER,
            accessibility_score INTEGER,
            best_practices_score INTEGER,
            mobile_score INTEGER,
            desktop_score INTEGER,
            recommendations TEXT,
            created_at TEXT,
            completed_at TEXT,
            error_message TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Simple auth
@app.post("/api/auth/login")
async def login(credentials: LoginRequest):
    if credentials.username == "admin" and credentials.password == "ArkBoosted2024!":
        return {"access_token": "simple_token", "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

# Audit endpoints
@app.post("/api/audits/", response_model=dict)
async def create_audit(audit: AuditCreate, background_tasks: BackgroundTasks):
    conn = sqlite3.connect('arkboosted_audits.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO audits (website_url, status, created_at)
        VALUES (?, ?, ?)
    ''', (audit.website_url, 'processing', datetime.utcnow().isoformat()))
    
    audit_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Process in background
    background_tasks.add_task(process_audit_simple, audit_id, audit.website_url)
    
    return {"id": audit_id, "website_url": audit.website_url, "status": "processing"}

@app.get("/api/audits/{audit_id}")
async def get_audit(audit_id: int):
    conn = sqlite3.connect('arkboosted_audits.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM audits WHERE id = ?', (audit_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    columns = ['id', 'website_url', 'status', 'grade', 'performance_score', 
               'seo_score', 'security_score', 'accessibility_score', 
               'best_practices_score', 'mobile_score', 'desktop_score',
               'recommendations', 'created_at', 'completed_at', 'error_message']
    
    audit_data = dict(zip(columns, row))
    
    # Parse recommendations if present
    if audit_data['recommendations']:
        try:
            audit_data['recommendations'] = json.loads(audit_data['recommendations'])
        except:
            pass
    
    return audit_data

@app.get("/api/audits/")
async def list_audits():
    conn = sqlite3.connect('arkboosted_audits.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM audits ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    columns = ['id', 'website_url', 'status', 'grade', 'performance_score', 
               'seo_score', 'security_score', 'accessibility_score', 
               'best_practices_score', 'mobile_score', 'desktop_score',
               'recommendations', 'created_at', 'completed_at', 'error_message']
    
    audits = []
    for row in rows:
        audit_data = dict(zip(columns, row))
        if audit_data['recommendations']:
            try:
                audit_data['recommendations'] = json.loads(audit_data['recommendations'])
            except:
                pass
        audits.append(audit_data)
    
    return audits

@app.delete("/api/audits/{audit_id}")
async def delete_audit(audit_id: int):
    conn = sqlite3.connect('arkboosted_audits.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM audits WHERE id = ?', (audit_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Audit not found")
    
    conn.commit()
    conn.close()
    return {"message": "Audit deleted"}

# PDF and Email endpoints
@app.get("/api/audits/{audit_id}/pdf")
async def download_pdf(audit_id: int):
    return {"message": f"PDF for audit {audit_id} would be generated here"}

@app.post("/api/audits/{audit_id}/email")
async def send_email(audit_id: int, email_data: dict):
    return {"message": f"Email sent for audit {audit_id} to {email_data.get('email', 'unknown')}"}

# Simple background processing
async def process_audit_simple(audit_id: int, website_url: str):
    await asyncio.sleep(5)  # Simulate processing time
    
    # Generate simple mock results
    performance_score = 75
    seo_score = 82
    security_score = 88
    accessibility_score = 79
    best_practices_score = 85
    mobile_score = 73
    desktop_score = 77
    
    # Calculate grade
    avg_score = (performance_score + seo_score + security_score + accessibility_score + best_practices_score) / 5
    if avg_score >= 90:
        grade = 'A'
    elif avg_score >= 80:
        grade = 'B'
    elif avg_score >= 70:
        grade = 'C'
    elif avg_score >= 60:
        grade = 'D'
    else:
        grade = 'F'
    
    recommendations = [
        "Optimize image compression and formats",
        "Implement proper caching headers", 
        "Minify CSS and JavaScript files",
        "Improve server response times",
        "Add missing alt tags to images"
    ]
    
    # Update database
    conn = sqlite3.connect('arkboosted_audits.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE audits SET 
            status = ?, grade = ?, performance_score = ?, seo_score = ?,
            security_score = ?, accessibility_score = ?, best_practices_score = ?,
            mobile_score = ?, desktop_score = ?, recommendations = ?,
            completed_at = ?
        WHERE id = ?
    ''', ('completed', grade, performance_score, seo_score, security_score,
          accessibility_score, best_practices_score, mobile_score, desktop_score,
          json.dumps(recommendations), datetime.utcnow().isoformat(), audit_id))
    
    conn.commit()
    conn.close()
    
    print(f"Audit {audit_id} completed with grade {grade}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
