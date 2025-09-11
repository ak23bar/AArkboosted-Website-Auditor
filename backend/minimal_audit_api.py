from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import requests
from datetime import datetime, timezone
import re
import json
import math
from bs4 import BeautifulSoup
import time

app = FastAPI(title="AArkboosted Minimal Audit API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DB_PATH = 'arkboosted_audits.db'
def init_db():
    try:
        print(f"Attempting to connect to database: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # First, create the table with all columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_url TEXT NOT NULL,
                website_type TEXT DEFAULT 'website',
                status TEXT DEFAULT 'completed',
                score INTEGER,
                strengths TEXT,
                improvements TEXT,
                recommendations TEXT,
                score_breakdown TEXT,
                created_at TEXT,
                completed_at TEXT
            )
        ''')
        
        # Check if website_type column exists in case this is an old database
        cursor.execute("PRAGMA table_info(audits)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'website_type' not in columns:
            cursor.execute('ALTER TABLE audits ADD COLUMN website_type TEXT DEFAULT "website"')
            print("Added website_type column to existing table")
            
        if 'score_breakdown' not in columns:
            cursor.execute('ALTER TABLE audits ADD COLUMN score_breakdown TEXT')
            print("Added score_breakdown column to existing table")
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise e

# Initialize database on startup
init_db()

class AuditCreate(BaseModel):
    website_url: str
    website_type: str = "website"

class AuditResponse(BaseModel):
    id: int
    website_url: str
    website_type: str
    status: str
    score: int
    strengths: List[str]
    improvements: List[str]
    recommendations: List[str]  # Keep for backward compatibility
    score_breakdown: Optional[dict] = None
    created_at: str
    completed_at: str

@app.get("/")
def health_check():
    return {"status": "healthy", "message": "AArkboosted Audit API is running"}

@app.get("/api/health")
def api_health():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM audits')
        count = cursor.fetchone()[0]
        conn.close()
        return {"status": "healthy", "database": "connected", "total_audits": count}
    except Exception as e:
        return {"status": "unhealthy", "database": "error", "error": str(e)}

@app.post("/api/audits/", response_model=AuditResponse)
def create_audit(audit: AuditCreate):
    try:
        url = audit.website_url
        website_type = audit.website_type
        created_at = datetime.now(timezone.utc).isoformat()
        completed_at = created_at
        
        # Use enhanced analysis for structured data
        analysis_result = analyze_website_enhanced(url, website_type)
        score = analysis_result['score']
        strengths = analysis_result['strengths']
        improvements = analysis_result['improvements']
        all_recommendations = analysis_result['all_recommendations']
        score_breakdown = analysis_result.get('score_breakdown', {})
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audits (website_url, website_type, status, score, recommendations, strengths, improvements, score_breakdown, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (url, website_type, 'completed', score, '\n'.join(all_recommendations), 
              '\n'.join(strengths), '\n'.join(improvements), json.dumps(score_breakdown), created_at, completed_at))
        audit_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return AuditResponse(
            id=audit_id,
            website_url=url,
            website_type=website_type,
            status='completed',
            score=score,
            recommendations=all_recommendations,
            strengths=strengths,
            improvements=improvements,
            score_breakdown=score_breakdown,
            created_at=created_at,
            completed_at=completed_at
        )
    except Exception as e:
        print(f"Error creating audit: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create audit: {str(e)}")

@app.get("/api/audits/{audit_id}", response_model=AuditResponse)
def get_audit(audit_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM audits WHERE id = ?', (audit_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Audit not found")
        
        # Handle different schema versions
        if len(row) >= 11:  # New schema with score_breakdown
            strengths = row[5].split('\n') if row[5] else []
            improvements = row[6].split('\n') if row[6] else []
            recommendations = row[7].split('\n') if row[7] else []
            score_breakdown = json.loads(row[10]) if row[10] else None
            return AuditResponse(
                id=row[0],
                website_url=row[1],
                website_type=row[2],
                status=row[3],
                score=row[4],
                recommendations=recommendations,
                strengths=strengths,
                improvements=improvements,
                score_breakdown=score_breakdown,
                created_at=row[8],
                completed_at=row[9]
            )
        elif len(row) >= 10:  # Schema with strengths and improvements but no score_breakdown
            strengths = row[5].split('\n') if row[5] else []
            improvements = row[6].split('\n') if row[6] else []
            recommendations = row[7].split('\n') if row[7] else []
            return AuditResponse(
                id=row[0],
                website_url=row[1],
                website_type=row[2],
                status=row[3],
                score=row[4],
                recommendations=recommendations,
                strengths=strengths,
                improvements=improvements,
                score_breakdown=None,
                created_at=row[8],
                completed_at=row[9]
            )
        elif len(row) >= 8:  # Schema with website_type but no strengths/improvements
            recommendations = row[5].split('\n') if row[5] else []
            # Split existing recommendations into strengths and improvements
            strengths = [rec for rec in recommendations if rec.startswith("✅")]
            improvements = [rec for rec in recommendations if rec.startswith("❌") or rec.startswith("⚠️")]
            return AuditResponse(
                id=row[0],
                website_url=row[1],
                website_type=row[2],
                status=row[3],
                score=row[4],
                recommendations=recommendations,
                strengths=strengths,
                improvements=improvements,
                score_breakdown=None,
                created_at=row[6],
                completed_at=row[7]
            )
        else:  # Old schema without website_type
            recommendations = row[4].split('\n') if row[4] else []
            strengths = [rec for rec in recommendations if rec.startswith("✅")]
            improvements = [rec for rec in recommendations if rec.startswith("❌") or rec.startswith("⚠️")]
            return AuditResponse(
                id=row[0],
                website_url=row[1],
                website_type="website",  # Default for old records
                status=row[2],
                score=row[3],
                recommendations=recommendations,
                strengths=strengths,
                improvements=improvements,
                score_breakdown=None,
                created_at=row[5],
                completed_at=row[6]
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting audit {audit_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit: {str(e)}")

@app.get("/api/audits/", response_model=List[AuditResponse])
def list_audits():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM audits ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        audits = []
        for row in rows:
            # Handle different schema versions
            if len(row) >= 11:  # New schema with score_breakdown
                strengths = row[5].split('\n') if row[5] else []
                improvements = row[6].split('\n') if row[6] else []
                recommendations = row[7].split('\n') if row[7] else []
                score_breakdown = json.loads(row[10]) if row[10] else None
                audits.append(AuditResponse(
                    id=row[0],
                    website_url=row[1],
                    website_type=row[2],
                    status=row[3],
                    score=row[4],
                    recommendations=recommendations,
                    strengths=strengths,
                    improvements=improvements,
                    score_breakdown=score_breakdown,
                    created_at=row[8],
                    completed_at=row[9]
                ))
            elif len(row) >= 10:  # Schema with strengths and improvements but no score_breakdown
                strengths = row[5].split('\n') if row[5] else []
                improvements = row[6].split('\n') if row[6] else []
                recommendations = row[7].split('\n') if row[7] else []
                audits.append(AuditResponse(
                    id=row[0],
                    website_url=row[1],
                    website_type=row[2],
                    status=row[3],
                    score=row[4],
                    recommendations=recommendations,
                    strengths=strengths,
                    improvements=improvements,
                    score_breakdown=None,
                    created_at=row[8],
                    completed_at=row[9]
                ))
            elif len(row) >= 8:  # Schema with website_type but no strengths/improvements
                recommendations = row[5].split('\n') if row[5] else []
                # Split existing recommendations into strengths and improvements
                strengths = [rec for rec in recommendations if rec.startswith("✅")]
                improvements = [rec for rec in recommendations if rec.startswith("❌") or rec.startswith("⚠️")]
                audits.append(AuditResponse(
                    id=row[0],
                    website_url=row[1],
                    website_type=row[2],
                    status=row[3],
                    score=row[4],
                    recommendations=recommendations,
                    strengths=strengths,
                    improvements=improvements,
                    score_breakdown=None,
                    created_at=row[6],
                    completed_at=row[7]
                ))
            else:  # Old schema without website_type
                recommendations = row[4].split('\n') if row[4] else []
                strengths = [rec for rec in recommendations if rec.startswith("✅")]
                improvements = [rec for rec in recommendations if rec.startswith("❌") or rec.startswith("⚠️")]
                audits.append(AuditResponse(
                    id=row[0],
                    website_url=row[1],
                    website_type="website",  # Default for old records
                    status=row[2],
                    score=row[3],
                    recommendations=recommendations,
                    strengths=strengths,
                    improvements=improvements,
                    score_breakdown=None,
                    created_at=row[5],
                    completed_at=row[6]
                ))
        return audits
    except Exception as e:
        print(f"Error listing audits: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list audits: {str(e)}")

@app.delete("/api/audits/")
def clear_all_audits():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM audits')
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        return {"message": f"Successfully deleted {deleted_count} audits"}
    except Exception as e:
        print(f"Error clearing audits: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear audits: {str(e)}")

@app.delete("/api/audits/{audit_id}")
def delete_audit(audit_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM audits WHERE id = ?', (audit_id,))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Audit not found")
        conn.commit()
        conn.close()
        return {"message": f"Successfully deleted audit {audit_id}"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting audit {audit_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete audit: {str(e)}")

def get_pagespeed_metrics(url: str):
    """
    Get real performance metrics from Google PageSpeed Insights API
    Falls back to manual timing if API key not available
    """
    try:
        # Free API (no key needed) - limited but gives core metrics
        api_url = f"https://www.googleapis.com/pagespeed/v5/runPagespeed?url={url}&strategy=mobile"
        
        response = requests.get(api_url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            
            # Extract Core Web Vitals
            lighthouse = data.get('lighthouseResult', {})
            audits = lighthouse.get('audits', {})
            
            metrics = {
                'performance_score': lighthouse.get('categories', {}).get('performance', {}).get('score', 0) * 100,
                'fcp': audits.get('first-contentful-paint', {}).get('numericValue', 0) / 1000,  # Convert to seconds
                'lcp': audits.get('largest-contentful-paint', {}).get('numericValue', 0) / 1000,
                'cls': audits.get('cumulative-layout-shift', {}).get('numericValue', 0),
                'fid': audits.get('first-input-delay', {}).get('numericValue', 0),
                'speed_index': audits.get('speed-index', {}).get('numericValue', 0) / 1000,
                'total_blocking_time': audits.get('total-blocking-time', {}).get('numericValue', 0),
            }
            return metrics
    except Exception as e:
        print(f"PageSpeed API error: {e}")
    
    # Fallback to manual timing
    try:
        start_time = time.time()
        response = requests.get(url, timeout=15)
        load_time = time.time() - start_time
        
        return {
            'performance_score': max(0, 100 - (load_time * 20)),  # Rough estimate
            'fcp': load_time,
            'lcp': load_time * 1.2,
            'cls': 0.1,  # Default estimate
            'fid': 100,  # Default estimate
            'speed_index': load_time * 1000,
            'total_blocking_time': 200,
        }
    except Exception as e:
        print(f"Manual timing error: {e}")
        return {
            'performance_score': 0,
            'fcp': 10,
            'lcp': 15,
            'cls': 0.5,
            'fid': 500,
            'speed_index': 8000,
            'total_blocking_time': 1000,
        }

def analyze_seo_advanced(html_content: str, url: str):
    """
    Advanced SEO analysis using BeautifulSoup for better parsing
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    seo_findings = {'score': 0, 'issues': [], 'strengths': []}
    
    # Title analysis
    title_tag = soup.find('title')
    if title_tag and title_tag.text:
        title_length = len(title_tag.text.strip())
        if 30 <= title_length <= 60:
            seo_findings['strengths'].append(f"✅ EXCELLENT: Perfect title length ({title_length} chars)")
            seo_findings['score'] += 25
        elif 15 <= title_length <= 80:
            seo_findings['strengths'].append(f"✅ Good title tag length ({title_length} chars)")
            seo_findings['score'] += 15
        else:
            seo_findings['issues'].append(f"⚠️ MAJOR: Poor title length ({title_length} chars)")
            seo_findings['score'] -= 10
    else:
        seo_findings['issues'].append("❌ CRITICAL: Missing or empty title tag")
        seo_findings['score'] -= 25
    
    # Meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        desc_length = len(meta_desc['content'].strip())
        if 140 <= desc_length <= 160:
            seo_findings['strengths'].append("✅ EXCELLENT: Perfect meta description length")
            seo_findings['score'] += 20
        elif 120 <= desc_length <= 180:
            seo_findings['strengths'].append("✅ Good meta description length")
            seo_findings['score'] += 15
        else:
            seo_findings['issues'].append("⚠️ Meta description length needs optimization")
            seo_findings['score'] += 5
    else:
        seo_findings['issues'].append("❌ CRITICAL: Missing meta description")
        seo_findings['score'] -= 20
    
    # Heading structure
    h1_tags = soup.find_all('h1')
    if len(h1_tags) == 1:
        h1_text = h1_tags[0].get_text().strip()
        if len(h1_text) >= 10:
            seo_findings['strengths'].append("✅ EXCELLENT: Perfect H1 structure")
            seo_findings['score'] += 20
        else:
            seo_findings['issues'].append("⚠️ H1 is too short")
            seo_findings['score'] += 10
    elif len(h1_tags) > 1:
        seo_findings['issues'].append(f"❌ MAJOR: Multiple H1 tags ({len(h1_tags)}) confuse search engines")
        seo_findings['score'] -= 15
    else:
        seo_findings['issues'].append("❌ CRITICAL: Missing H1 heading")
        seo_findings['score'] -= 20
    
    # Image optimization
    images = soup.find_all('img')
    if images:
        images_with_alt = [img for img in images if img.get('alt')]
        alt_ratio = len(images_with_alt) / len(images)
        if alt_ratio >= 0.9:
            seo_findings['strengths'].append(f"✅ EXCELLENT: Great image accessibility ({len(images_with_alt)}/{len(images)} have alt text)")
            seo_findings['score'] += 15
        elif alt_ratio >= 0.7:
            seo_findings['strengths'].append("✅ Good image accessibility")
            seo_findings['score'] += 10
        else:
            seo_findings['issues'].append(f"❌ MAJOR: Poor accessibility - only {len(images_with_alt)}/{len(images)} images have alt text")
            seo_findings['score'] -= 10
    
    # Structured data
    json_ld = soup.find_all('script', type='application/ld+json')
    if json_ld:
        seo_findings['strengths'].append("✅ EXCELLENT: Structured data found (Schema.org)")
        seo_findings['score'] += 15
    
    # Social media tags
    og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
    twitter_tags = soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')})
    
    if og_tags and twitter_tags:
        seo_findings['strengths'].append("✅ EXCELLENT: Complete social media optimization")
        seo_findings['score'] += 10
    elif og_tags or twitter_tags:
        seo_findings['strengths'].append("✅ Good social media tags present")
        seo_findings['score'] += 5
    else:
        seo_findings['issues'].append("⚠️ Missing social media optimization (Open Graph/Twitter Cards)")
        seo_findings['score'] -= 5
    
    # AI Services Detection
    page_text = soup.get_text().lower()
    script_content = ' '.join([script.get_text() for script in soup.find_all('script')])
    
    ai_services_detected = []
    
    # Check for various AI services
    ai_services = {
        'elevenlabs': ['elevenlabs', 'eleven labs', 'text-to-speech ai', 'voice synthesis'],
        'openai': ['openai', 'gpt-', 'chatgpt', 'dall-e', 'whisper'],
        'anthropic': ['anthropic', 'claude'],
        'google_ai': ['google ai', 'bard', 'gemini', 'tensorflow'],
        'aws_ai': ['aws ai', 'amazon ai', 'sagemaker', 'rekognition', 'polly'],
        'azure_ai': ['azure ai', 'cognitive services', 'azure openai'],
        'huggingface': ['hugging face', 'transformers', 'diffusers'],
        'stability': ['stability ai', 'stable diffusion'],
        'cohere': ['cohere', 'co:here'],
        'replicate': ['replicate.com', 'replicate ai'],
        'midjourney': ['midjourney', 'discord bot'],
        'runwayml': ['runway ml', 'runwayml']
    }
    
    for service, keywords in ai_services.items():
        if any(keyword in page_text or keyword in script_content.lower() for keyword in keywords):
            ai_services_detected.append(service)
    
    # Check for AI-related API calls in scripts
    ai_apis = ['api.openai.com', 'api.elevenlabs.io', 'api.anthropic.com', 'api.cohere.ai']
    for api in ai_apis:
        if api in script_content:
            service_name = api.split('.')[1] if '.' in api else api
            if service_name not in ai_services_detected:
                ai_services_detected.append(service_name)
    
    # Award points for AI integration
    if ai_services_detected:
        service_names = ', '.join([s.replace('_', ' ').title() for s in ai_services_detected])
        if len(ai_services_detected) >= 3:
            seo_findings['strengths'].append(f"🤖 EXCELLENT: Advanced AI integration detected ({service_names})")
            seo_findings['score'] += 20
        elif len(ai_services_detected) >= 2:
            seo_findings['strengths'].append(f"🤖 Good AI services integration ({service_names})")
            seo_findings['score'] += 15
        else:
            seo_findings['strengths'].append(f"🤖 AI-powered features detected ({service_names})")
            seo_findings['score'] += 10
    
    return seo_findings

def analyze_ui_ux_quality(html_content: str, url: str):
    """
    Comprehensive UI/UX analysis to detect poor design, spacing, default content, and usability issues
    Enhanced to detect and heavily penalize template-based websites and website builders
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    uiux_findings = {
        'strengths': [],
        'issues': [],
        'score': 0
    }
    
    page_text = soup.get_text().strip()
    visible_text = ' '.join(page_text.split())
    html_lower = html_content.lower()
    
    # 1. WEBSITE BUILDER AND TEMPLATE DETECTION (MORE SPECIFIC)
    website_builder_indicators = {
        'godaddy': ['gd-marketing', 'websitebuilder.secureserver', 'gdwebsites', 'godaddy-widget', 'airo-'],
        'wix': ['wixstatic.com', 'parastorage.com', 'wixsite.com'],
        'squarespace': ['squarespacestatic', 'squarespace-cdn', 'sqsp.com'],
        'weebly': ['weeblycloud', 'weebly-'],
        'shopify': ['shopifycdn', 'myshopify.com'],
        'webflow': ['webflow-'],
    }
    
    detected_builder = None
    builder_score_penalty = 0
    
    for builder_name, indicators in website_builder_indicators.items():
        for indicator in indicators:
            if indicator in html_lower:
                detected_builder = builder_name
                if builder_name == 'godaddy':
                    builder_score_penalty = 40  # Heavy penalty for GoDaddy sites
                    uiux_findings['issues'].append("🚨 CRITICAL: GoDaddy website builder - limited design flexibility")
                elif builder_name in ['wix', 'squarespace', 'weebly']:
                    builder_score_penalty = 25  # Moderate penalty for basic builders
                    uiux_findings['issues'].append(f"⚠️ MAJOR: {builder_name.title()} template - may limit customization")
                else:
                    builder_score_penalty = 15
                    uiux_findings['issues'].append(f"⚠️ Website builder detected: {builder_name.title()}")
                break
        if detected_builder:
            break
    
    uiux_findings['score'] -= builder_score_penalty

    # 2. TEMPLATE-SPECIFIC DEFAULT CONTENT DETECTION (ENHANCED)
    default_content_patterns = [
        # Generic placeholders (more specific patterns)
        'lorem ipsum', 'placeholder text', 'sample text', 'dummy text',
        'your content here', 'add your content', 'click here to edit',
        'default text', 'example text', 'test content', 'coming soon',
        'under construction', 'website under development',
        'john doe', 'jane doe', 'your name here', 'company name',
        'your email here', 'example@email.com', 'test@test.com',
        'replace this text', 'edit this section', 'add description here',
        # Note: Removed 'demo video placeholder' as it's legitimate for portfolios
    ]

    default_issues = []
    for pattern in default_content_patterns:
        if pattern in visible_text.lower():
            # Avoid false positives by checking context
            if pattern == 'template' and ('template programming' in visible_text.lower() or 'portfolio templates' in visible_text.lower()):
                continue  # Skip if it's about programming skills
            if 'placeholder=' in html_content.lower() and pattern in ['placeholder', 'enter command']:
                continue  # Skip HTML placeholder attributes
            if pattern == 'coming soon' and ('demo video coming soon' in visible_text.lower()):
                continue  # Skip legitimate "coming soon" for demo videos in portfolios
            default_issues.append(pattern)

    if default_issues:
        penalty = len(default_issues) * 8
        uiux_findings['issues'].append(f"🚨 CRITICAL: Default/template content found ({len(default_issues)} instances)")
        uiux_findings['score'] -= penalty
    elif len(visible_text.split()) > 100:  # Only give credit for substantial custom content
        uiux_findings['score'] += 5  # Reduced from 15

    # 2. ENHANCED TYPOGRAPHY AND SPACING ANALYSIS
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    paragraphs = soup.find_all('p')
    
    # Check for proper heading hierarchy
    heading_sizes = [int(h.name[1]) for h in headings if h.get_text().strip()]
    if heading_sizes:
        proper_hierarchy = all(heading_sizes[i] <= heading_sizes[i+1] + 1 for i in range(len(heading_sizes)-1))
        if proper_hierarchy and len(set(heading_sizes)) >= 3:
            uiux_findings['score'] += 10  # Reduced from 15
        elif proper_hierarchy and len(set(heading_sizes)) >= 2:
            uiux_findings['score'] += 5  # Reduced from 8
        else:
            penalty = 20 if detected_builder else 12
            uiux_findings['issues'].append("🚨 Poor typography hierarchy - unprofessional appearance")
            uiux_findings['score'] -= penalty
    elif len(headings) == 0 and len(visible_text.split()) > 100:
        penalty = 25 if detected_builder else 15
        uiux_findings['issues'].append("🚨 CRITICAL: No headings - poor content structure")
        uiux_findings['score'] -= penalty
    
    # Enhanced paragraph and spacing analysis
    long_paragraphs = [p for p in paragraphs if len(p.get_text().split()) > 100]
    very_long_paragraphs = [p for p in paragraphs if len(p.get_text().split()) > 200]
    
    if very_long_paragraphs:
        penalty = 20 if detected_builder else 15
        uiux_findings['issues'].append("🚨 Poor readability - text walls without proper breaks")
        uiux_findings['score'] -= penalty
    elif len(long_paragraphs) > len(paragraphs) * 0.6:
        penalty = 15 if detected_builder else 10
        uiux_findings['issues'].append("⚠️ Poor text formatting - paragraphs too long")
        uiux_findings['score'] -= penalty
    
    # 3. NAVIGATION AND STRUCTURE ANALYSIS
    nav_elements = soup.find_all(['nav', 'header']) + soup.find_all(class_=lambda x: x and 'nav' in x.lower())
    if nav_elements:
        nav_links = []
        for nav in nav_elements:
            nav_links.extend(nav.find_all('a'))
        
        if len(nav_links) >= 3:
            uiux_findings['strengths'].append("✅ Clear navigation structure")
            uiux_findings['score'] += 10
        elif len(nav_links) >= 1:
            uiux_findings['strengths'].append("✅ Basic navigation present")
            uiux_findings['score'] += 5
        else:
            uiux_findings['issues'].append("⚠️ Limited navigation - may confuse users")
            uiux_findings['score'] -= 5
    else:
        uiux_findings['issues'].append("🚨 CRITICAL: No clear navigation structure")
        uiux_findings['score'] -= 15
    
    # 4. IMAGE AND MEDIA QUALITY ANALYSIS (More Critical)
    images = soup.find_all('img')
    if images:
        # Check for missing alt tags (accessibility issue)
        missing_alt = len([img for img in images if not img.get('alt') or not img.get('alt').strip()])
        if missing_alt > 0:
            uiux_findings['issues'].append(f"🚨 CRITICAL: {missing_alt}/{len(images)} images missing alt text - accessibility violation")
            uiux_findings['score'] -= missing_alt * 3
        
        # Check for generic/stock image patterns
        generic_image_patterns = [
            'placeholder', 'stock-photo', 'generic', 'default-image',
            'sample-image', 'temp-image', 'test-image', '150x150',
            'via.placeholder', 'picsum.photos', 'lorempixel'
        ]
        
        generic_images = 0
        for img in images:
            src = img.get('src', '').lower()
            alt = img.get('alt', '').lower()
            if any(pattern in src or pattern in alt for pattern in generic_image_patterns):
                generic_images += 1
        
        if generic_images > len(images) * 0.3:
            uiux_findings['issues'].append(f"⚠️ Too many generic/placeholder images ({generic_images}/{len(images)})")
            uiux_findings['score'] -= 15
        
        # Check for oversized images (performance issue)
        large_images = 0
        for img in images:
            src = img.get('src', '')
            # Basic heuristic for large images
            if any(size in src.lower() for size in ['2000', '4000', 'full', 'original']):
                large_images += 1
        
        if large_images > 0:
            uiux_findings['issues'].append(f"⚠️ {large_images} potentially oversized images - may slow loading")
            uiux_findings['score'] -= large_images * 5
    
    # 5. FORM AND INTERACTION QUALITY
    forms = soup.find_all('form')
    inputs = soup.find_all(['input', 'textarea', 'select'])
    
    if forms and inputs:
        # Check for proper labeling
        labels = soup.find_all('label')
        labeled_inputs = len([inp for inp in inputs if inp.get('id') in [l.get('for') for l in labels]])
        
        if labeled_inputs >= len(inputs) * 0.8:
            uiux_findings['strengths'].append("✅ EXCELLENT: Well-labeled forms for accessibility")
            uiux_findings['score'] += 10
        elif labeled_inputs >= len(inputs) * 0.5:
            uiux_findings['strengths'].append("✅ Good form labeling")
            uiux_findings['score'] += 5
        else:
            uiux_findings['issues'].append("⚠️ Poor form accessibility - missing labels")
            uiux_findings['score'] -= 8
    
    # 6. ENHANCED LAYOUT AND SPACING DETECTION
    # Check for common CSS layout issues
    style_elements = soup.find_all('style')
    inline_styles = [elem.get('style', '') for elem in soup.find_all() if elem.get('style')]
    
    all_styles = ' '.join([style.get_text() for style in style_elements] + inline_styles)
    
    # Detect poor template spacing patterns
    poor_spacing_indicators = [
        'margin: 0', 'padding: 0', 'margin:0', 'padding:0',
        'margin: auto', 'padding: 10px', 'margin: 10px',
        # Common template/builder spacing issues
        'margin: 5px', 'padding: 5px', 'line-height: 1',
        'letter-spacing: normal', 'word-spacing: normal'
    ]
    
    template_spacing_count = sum(1 for indicator in poor_spacing_indicators if indicator in all_styles.lower())
    
    # Check for modern layout techniques
    modern_layout_indicators = ['flexbox', 'grid', 'flex', 'display: flex', 'display: grid', 'css grid']
    custom_layout_indicators = ['max-width', 'min-width', 'media query', '@media', 'responsive']
    
    has_modern_layout = any(indicator in all_styles.lower() for indicator in modern_layout_indicators)
    has_custom_responsive = any(indicator in all_styles.lower() for indicator in custom_layout_indicators)
    
    # Analyze layout quality
    if detected_builder and template_spacing_count > 3:
        uiux_findings['issues'].append("🚨 CRITICAL: Template-based spacing - unprofessional layout")
        uiux_findings['score'] -= 20
    elif template_spacing_count > 5:
        uiux_findings['issues'].append("🚨 Poor spacing consistency - amateur design")
        uiux_findings['score'] -= 15
    elif has_modern_layout and has_custom_responsive:
        uiux_findings['strengths'].append("✅ EXCELLENT: Professional layout with modern CSS techniques")
        uiux_findings['score'] += 15
    elif has_modern_layout:
        uiux_findings['strengths'].append("✅ Good modern layout techniques")
        uiux_findings['score'] += 8
    
    # Check for template-specific layout issues
    template_layout_issues = [
        'position: absolute', 'float: left', 'float: right', 'clear: both',
        'table-layout', 'vertical-align: top'
    ]
    
    old_layout_count = sum(1 for indicator in template_layout_issues if indicator in all_styles.lower())
    if old_layout_count > 2 and detected_builder:
        uiux_findings['issues'].append("🚨 Outdated layout techniques - template-based design")
        uiux_findings['score'] -= 12
        uiux_findings['strengths'].append("✅ Custom spacing and layout")
        uiux_findings['score'] += 5
    
    # 7. CONTENT QUALITY AND TYPOS (More Critical)
    # Basic spell check for common typos
    common_typos = [
        'recieve', 'seperate', 'occured', 'necesary', 'begining', 'writting',
        'comming', 'runing', 'geting', 'makeing', 'takeing', 'giveing',
        'definately', 'independant', 'accomodate', 'embarass', 'occurance',
        'recomend', 'wierd', 'freind', 'beleive', 'recieved'
    ]
    
    typos_found = []
    words = visible_text.lower().split()
    for word in words:
        clean_word = ''.join(c for c in word if c.isalpha())
        if clean_word in common_typos:
            typos_found.append(clean_word)
    
    if typos_found:
        uiux_findings['issues'].append(f"🚨 CRITICAL: Spelling errors detected - unprofessional ({len(set(typos_found))} unique typos)")
        uiux_findings['score'] -= len(set(typos_found)) * 5  # Increased penalty
    
    # Check for poor grammar patterns
    poor_grammar_patterns = [
        'i am', 'we is', 'they was', 'dont', 'cant', 'wont', 'youre', 'its a',
        'alot', 'everytime', 'everyday' # common grammar mistakes
    ]
    
    grammar_issues = []
    for pattern in poor_grammar_patterns:
        if pattern in visible_text.lower():
            grammar_issues.append(pattern)
    
    if len(grammar_issues) > 2:
        uiux_findings['issues'].append(f"⚠️ Grammar/punctuation issues detected - affects professionalism")
        uiux_findings['score'] -= len(grammar_issues) * 2
    
    # 8. CALL-TO-ACTION ANALYSIS
    cta_keywords = ['contact', 'buy', 'purchase', 'sign up', 'subscribe', 'download', 'get started', 'learn more']
    buttons = soup.find_all(['button', 'a'])
    
    cta_buttons = 0
    for button in buttons:
        button_text = button.get_text().lower().strip()
        if any(keyword in button_text for keyword in cta_keywords) and len(button_text) < 50:
            cta_buttons += 1
    
    if cta_buttons >= 2:
        uiux_findings['strengths'].append("✅ EXCELLENT: Clear call-to-action elements")
        uiux_findings['score'] += 12
    elif cta_buttons >= 1:
        uiux_findings['strengths'].append("✅ Call-to-action present")
        uiux_findings['score'] += 6
    else:
        uiux_findings['issues'].append("⚠️ Missing clear call-to-action elements")
        uiux_findings['score'] -= 8
    
    # 9. MOBILE-FIRST DESIGN INDICATORS
    meta_viewport = soup.find('meta', attrs={'name': 'viewport'})
    if meta_viewport:
        content = meta_viewport.get('content', '')
        if 'width=device-width' in content:
            uiux_findings['strengths'].append("✅ Mobile-responsive viewport configuration")
            uiux_findings['score'] += 8
    
    # 10. FINAL TEMPLATE/BUILDER QUALITY ASSESSMENT
    if detected_builder:
        # Template sites should be heavily penalized for lack of custom design
        total_custom_indicators = len([item for item in uiux_findings['strengths'] if 'EXCELLENT' in item])
        total_template_issues = len([item for item in uiux_findings['issues'] if 'CRITICAL' in item or 'template' in item.lower()])
        
        if total_template_issues >= 3:
            uiux_findings['issues'].append("🚨 OVERALL: Multiple template/design quality issues detected")
            uiux_findings['score'] -= 15
        elif total_custom_indicators == 0:
            uiux_findings['issues'].append("🚨 OVERALL: Template-based site lacks professional customization")
            uiux_findings['score'] -= 10
    
    # Ensure template sites can't score too high
    if detected_builder == 'godaddy':
        uiux_findings['score'] = min(uiux_findings['score'], 25)  # Cap GoDaddy sites at 25/100
        uiux_findings['issues'].append("🚨 OVERALL: GoDaddy template severely limits professional design quality")
    elif detected_builder in ['wix', 'weebly', 'site123'] and uiux_findings['score'] > 50:
        uiux_findings['score'] = min(uiux_findings['score'], 35)  # Cap basic template sites at 35/100
        uiux_findings['issues'].append("🚨 OVERALL: Template-based design limits professional appearance")
    
    return uiux_findings

def ai_powered_analysis(url: str, website_type: str = 'website'):
    """
    AI-powered comprehensive website analysis with real metrics
    """
    print(f"🤖 Starting AI-powered analysis for {website_type}: {url}")
    
    # Ensure URL has protocol
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    analysis_results = {
        'score': 0,
        'strengths': [],
        'issues': [],
        'performance_metrics': {},
        'breakdown': {}
    }
    
    try:
        # 1. Get real performance metrics
        print("📊 Fetching performance metrics...")
        perf_metrics = get_pagespeed_metrics(url)
        analysis_results['performance_metrics'] = perf_metrics
        
        # 2. Fetch website content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        load_time = time.time() - start_time
        
        if response.status_code != 200:
            analysis_results['issues'].append(f"❌ CRITICAL: Website returned error {response.status_code}")
            return 5, analysis_results['issues'] + analysis_results['strengths']
        
        # 3. Security Analysis
        security_score = 0
        if response.url.startswith('https://'):
            analysis_results['strengths'].append("✅ Website uses HTTPS encryption")
            security_score += 30
        else:
            analysis_results['issues'].append("❌ CRITICAL: No HTTPS - major security risk")
            security_score -= 30
        
        # 4. Performance Analysis using real metrics (FOCUS ON ISSUES)
        performance_score = 0
        perf_score = perf_metrics.get('performance_score', 0)
        
        if perf_score >= 90:
            # Only give credit for truly exceptional performance
            analysis_results['strengths'].append(f"✅ Outstanding performance ({perf_score:.0f}/100)")
            performance_score += 40
        elif perf_score >= 70:
            performance_score += 25
        elif perf_score >= 50:
            analysis_results['issues'].append(f"⚠️ MAJOR: Below average performance ({perf_score:.0f}/100) - users expect faster loading")
            performance_score += 10
        else:
            analysis_results['issues'].append(f"❌ CRITICAL: Poor performance ({perf_score:.0f}/100) - major user experience issue")
            performance_score -= 20
        
        # Core Web Vitals analysis - FOCUS ON PROBLEMS
        fcp = perf_metrics.get('fcp', 10)
        lcp = perf_metrics.get('lcp', 15) 
        cls = perf_metrics.get('cls', 0.5)
        
        # Only highlight truly excellent metrics, focus on issues
        if fcp <= 1.8:
            performance_score += 15
        elif fcp <= 3.0:
            performance_score += 10
        else:
            analysis_results['issues'].append(f"❌ MAJOR: Slow First Contentful Paint ({fcp:.1f}s) - users see blank page too long")
            performance_score -= 10
        
        if lcp <= 2.5:
            performance_score += 15
        elif lcp <= 4.0:
            analysis_results['issues'].append(f"⚠️ MAJOR: Largest Contentful Paint needs improvement ({lcp:.1f}s)")
            performance_score += 5
        else:
            analysis_results['issues'].append(f"❌ CRITICAL: Slow Largest Contentful Paint ({lcp:.1f}s) - poor user experience")
            performance_score -= 15
        
        if cls <= 0.1:
            performance_score += 10
        elif cls <= 0.25:
            analysis_results['issues'].append(f"⚠️ Layout shift detected (CLS: {cls:.3f}) - elements jump around")
            performance_score += 3
        else:
            analysis_results['issues'].append(f"❌ MAJOR: Significant layout shift (CLS: {cls:.3f}) - very poor user experience")
            performance_score -= 10
        
        # 5. Advanced SEO Analysis
        print("🔍 Analyzing SEO...")
        seo_analysis = analyze_seo_advanced(response.text, url)
        seo_score = seo_analysis['score']
        analysis_results['strengths'].extend(seo_analysis['strengths'])
        analysis_results['issues'].extend(seo_analysis['issues'])
        
        # 6. UI/UX Quality Analysis
        print("🎨 Analyzing UI/UX quality...")
        uiux_analysis = analyze_ui_ux_quality(response.text, url)
        uiux_score = uiux_analysis['score']
        analysis_results['strengths'].extend(uiux_analysis['strengths'])
        analysis_results['issues'].extend(uiux_analysis['issues'])
        
        # 7. Mobile Responsiveness - FOCUS ON ISSUES
        mobile_score = 0
        soup = BeautifulSoup(response.text, 'html.parser')
        viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
        
        if viewport_tag:
            mobile_score += 40  # Don't over-praise basic requirements
        else:
            analysis_results['issues'].append("❌ CRITICAL: No viewport tag - website breaks on mobile devices")
            mobile_score -= 30
        
        # Check for responsive CSS
        css_content = response.text.lower()
        responsive_indicators = ['@media', 'max-width', 'min-width', 'responsive', 'mobile-first']
        responsive_count = sum(1 for indicator in responsive_indicators if indicator in css_content)
        
        if responsive_count >= 3:
            mobile_score += 15  # Reduced praise
        elif responsive_count >= 1:
            mobile_score += 8
        else:
            analysis_results['issues'].append("❌ MAJOR: No responsive design detected - poor mobile experience")
            mobile_score -= 20
        
        # 7. Content Quality Analysis for different website types
        content_score = 0
        word_count = len(re.findall(r'\b\w+\b', soup.get_text()))
        
        if website_type == 'portfolio':
            # Portfolio sites should showcase work, not have tons of text
            if 200 <= word_count <= 1000:
                analysis_results['strengths'].append(f"✅ EXCELLENT: Perfect content amount for portfolio ({word_count} words)")
                content_score += 25
            elif word_count < 200:
                analysis_results['issues'].append(f"⚠️ Consider adding more project descriptions ({word_count} words)")
                content_score += 10
            else:
                analysis_results['strengths'].append(f"✅ Rich content for portfolio ({word_count} words)")
                content_score += 20
        elif website_type == 'landing-page':
            if 300 <= word_count <= 800:
                analysis_results['strengths'].append(f"✅ EXCELLENT: Perfect landing page content length ({word_count} words)")
                content_score += 25
            else:
                analysis_results['issues'].append(f"⚠️ Consider optimizing content length for landing page ({word_count} words)")
                content_score += 10
        else:
            if word_count >= 300:
                analysis_results['strengths'].append(f"✅ Good content volume ({word_count} words)")
                content_score += 20
            else:
                analysis_results['issues'].append(f"⚠️ MAJOR: Very minimal content ({word_count} words)")
                content_score -= 10
        
        # 8. Calculate weighted final score based on website type
        type_weights = {
            'portfolio': {'security': 0.10, 'performance': 0.30, 'seo': 0.15, 'mobile': 0.20, 'content': 0.05, 'uiux': 0.20},
            'landing-page': {'security': 0.15, 'performance': 0.20, 'seo': 0.25, 'mobile': 0.15, 'content': 0.05, 'uiux': 0.20},
            'search-engine': {'security': 0.25, 'performance': 0.40, 'seo': 0.05, 'mobile': 0.20, 'content': 0.05, 'uiux': 0.05},
            'e-commerce': {'security': 0.25, 'performance': 0.20, 'seo': 0.15, 'mobile': 0.15, 'content': 0.05, 'uiux': 0.20},
            'blog': {'security': 0.10, 'performance': 0.15, 'seo': 0.35, 'mobile': 0.20, 'content': 0.10, 'uiux': 0.10},
            'website': {'security': 0.15, 'performance': 0.20, 'seo': 0.20, 'mobile': 0.20, 'content': 0.10, 'uiux': 0.15},
        }
        
        weights = type_weights.get(website_type, type_weights['website'])
        
        # COMPUTER SCIENCE BASED SCORING ALGORITHM
        # Uses Min-Max Normalization, Weighted Aggregation, and Statistical Penalty Functions
        
        # Step 1: STRICTER Min-Max Normalization - most sites should start lower
        def normalize_score(raw_score, min_expected=-50, max_expected=50, base=45):
            """
            MUCH STRICTER normalization - lower baselines, harder to achieve high scores
            Formula: base + ((raw_score - min_expected) / (max_expected - min_expected)) * (80 - base)
            """
            if max_expected == min_expected:
                return base
            # Cap max achievable score at 80, not 100
            normalized = base + ((raw_score - min_expected) / (max_expected - min_expected)) * (80 - base)
            return max(10, min(100, normalized))
        
        # Apply MUCH STRICTER normalization - most sites should start around 30-50
        security_score = normalize_score(security_score, -30, 30, 35)      # Security starts at 35 (was 65)
        performance_score = normalize_score(performance_score, -40, 40, 30) # Performance starts at 30 (was 60)  
        seo_score = normalize_score(seo_score, -25, 35, 40)               # SEO starts at 40 (was 70)
        mobile_score = normalize_score(mobile_score, -30, 30, 45)         # Mobile starts at 45 (was 75)
        content_score = normalize_score(content_score, -20, 40, 45)       # Content starts at 45 (was 75)
        uiux_score = normalize_score(uiux_score, -35, 35, 30)             # UI/UX starts at 30 (was 70)
        
        print(f"🔢 STRICTER Normalized Scores: SEC={security_score:.1f}, PERF={performance_score:.1f}, SEO={seo_score:.1f}, MOB={mobile_score:.1f}, CONT={content_score:.1f}, UI={uiux_score:.1f}")
        
        # Step 2: MUCH HEAVIER penalties for issues
        critical_issues = len([item for item in analysis_results['issues'] if '❌ CRITICAL' in item])
        major_issues = len([item for item in analysis_results['issues'] if '❌ MAJOR' in item or '⚠️ MAJOR' in item])
        template_issues = len([item for item in analysis_results['issues'] if any(builder in item.lower() for builder in ['godaddy', 'wix', 'squarespace', 'weebly', 'template', 'builder'])])
        godaddy_detected = any('godaddy' in item.lower() for item in analysis_results['issues'])
        
        # MUCH HEAVIER penalty function
        import math
        
        def exponential_penalty(issue_count, max_penalty, decay_factor=0.8):
            if issue_count == 0:
                return 0
            return max_penalty * (1 - math.exp(-decay_factor * issue_count))
        
        critical_penalty = exponential_penalty(critical_issues, 35, 0.9)  # Max 35 points (was 25)
        major_penalty = exponential_penalty(major_issues, 25, 0.8)        # Max 25 points (was 15)
        
        # MUCH HEAVIER template penalties
        template_penalty = 0
        if godaddy_detected:
            template_penalty = 25  # Heavy penalty for GoDaddy (was 12)
        elif template_issues > 0:
            template_penalty = 18  # Heavy penalty for any template (was 8)
        
        print(f"⚡ HEAVY Penalties: Critical={critical_penalty:.1f}, Major={major_penalty:.1f}, Template={template_penalty:.1f}")
        
        # Step 3: Same weighted aggregation
        base_score = (
            security_score * weights['security'] +
            performance_score * weights['performance'] +
            seo_score * weights['seo'] +
            mobile_score * weights['mobile'] +
            content_score * weights['content'] +
            uiux_score * weights['uiux']
        )
        
        # Apply MUCH HEAVIER penalties
        total_penalty = critical_penalty + major_penalty + template_penalty
        final_score = base_score - total_penalty
        
        # Step 4: FAIRER quality caps - don't over-penalize single issues
        if critical_issues >= 3:
            final_score = min(final_score, 35)  # Multiple critical = bad site
        elif critical_issues >= 2:
            final_score = min(final_score, 55)  # Two critical issues
        # Remove single critical issue cap - let the penalty handle it naturally
        
        # FAIRER major issue thresholds
        if major_issues >= 5:
            final_score = min(final_score, 45)  # Many major issues
        elif major_issues >= 3:
            final_score = min(final_score, 60)  # Several major issues
        
        # MUCH STRICTER template quality caps
        if godaddy_detected:
            final_score = min(final_score, 25)  # GoDaddy capped at 25 (was 45)
        elif template_issues >= 2:
            final_score = min(final_score, 35)  # (was 60)
        elif template_issues >= 1:
            final_score = min(final_score, 50)  # Templates capped at 50
        
        # Additional reality checks
        total_issues = critical_issues + major_issues + template_issues
        if total_issues >= 5:
            final_score = min(final_score, 25)
        elif total_issues >= 3:
            final_score = min(final_score, 40)
        
        # Final STRICT clamping - max score 90, not 100
        final_score = max(5, min(90, round(final_score)))
        
        print(f"🎯 REALISTIC Final Score: {final_score}/100 (Base: {base_score:.1f}, Penalties: -{total_penalty:.1f})")
        print(f"📊 Issue Analysis: {critical_issues} critical, {major_issues} major, {template_issues} template issues")
        
        analysis_results['score'] = final_score
        
        # Step 5: PROPER Mathematical Breakdown - Show ACTUAL Contributions
        # Calculate what each category ACTUALLY contributes to the final score
        raw_contributions = {
            'security': security_score * weights['security'],
            'performance': performance_score * weights['performance'],
            'seo': seo_score * weights['seo'],
            'mobile': mobile_score * weights['mobile'],
            'content': content_score * weights['content'],
            'uiux': uiux_score * weights['uiux']
        }
        
        # The base score before penalties
        base_weighted_score = sum(raw_contributions.values())
        
        # SHOW THE REAL BREAKDOWN: Base Score - Penalties = Final Score
        # Don't adjust the contributions - show them as they really are
        adjusted_contributions = {}
        for category, raw_contribution in raw_contributions.items():
            # Show the actual weighted contribution, not some adjusted fake number
            adjusted_contributions[category] = round(raw_contribution, 1)
        
        # The math should be: sum(contributions) - penalties = final_score
        expected_before_penalties = sum(adjusted_contributions.values())
        mathematical_check = expected_before_penalties - total_penalty
        
        print(f"📐 REAL Math Check: Weighted={expected_before_penalties:.1f} - Penalties={total_penalty:.1f} = {mathematical_check:.1f} (Final={final_score})")
        
        # If there's still a discrepancy due to caps, show it clearly
        cap_adjustment = final_score - mathematical_check if mathematical_check != final_score else 0
        
        # Return properly structured results with exact mathematical breakdown
        return {
            'score': final_score,
            'strengths': analysis_results['strengths'],
            'improvements': analysis_results['issues'],
            'all_recommendations': analysis_results['issues'] + analysis_results['strengths'],
            'score_breakdown': {
                'security': {
                    'score': int(round(security_score)), 
                    'weight': int(weights['security'] * 100),
                    'contribution': adjusted_contributions['security']
                },
                'performance': {
                    'score': int(round(performance_score)), 
                    'weight': int(weights['performance'] * 100),
                    'contribution': adjusted_contributions['performance']
                },
                'seo': {
                    'score': int(round(seo_score)), 
                    'weight': int(weights['seo'] * 100),
                    'contribution': adjusted_contributions['seo']
                },
                'mobile': {
                    'score': int(round(mobile_score)), 
                    'weight': int(weights['mobile'] * 100),
                    'contribution': adjusted_contributions['mobile']
                },
                'content': {
                    'score': int(round(content_score)), 
                    'weight': int(weights['content'] * 100),
                    'contribution': adjusted_contributions['content']
                },
                'uiux': {
                    'score': int(round(uiux_score)), 
                    'weight': int(weights['uiux'] * 100),
                    'contribution': adjusted_contributions['uiux']
                },
                'calculation': {
                    'base_weighted_score': round(base_weighted_score, 1),
                    'critical_penalty': round(critical_penalty, 1),
                    'major_penalty': round(major_penalty, 1), 
                    'template_penalty': round(template_penalty, 1),
                    'total_penalty': round(total_penalty, 1),
                    'before_caps': round(mathematical_check, 1),
                    'quality_cap_adjustment': round(cap_adjustment, 1),
                    'final_score': final_score,
                    'contribution_total': round(sum(adjusted_contributions.values()), 1),
                    'verification': f'REAL MATH: {base_weighted_score:.1f} - {total_penalty:.1f} - {abs(cap_adjustment):.1f} = {final_score}',
                    'algorithm': 'Strict-Weighted-Scoring + Heavy-Penalties + Quality-Caps'
                },
                'website_type': website_type,
                'critical_issues': critical_issues,
                'major_issues': major_issues,
                'template_issues': template_issues,
                'quality_thresholds_applied': {
                    'critical_cap': final_score == 35 and critical_issues >= 3,
                    'major_cap': final_score == 55 and major_issues >= 5,
                    'template_cap': final_score == 45 and godaddy_detected
                }
            }
        }
        
    except Exception as e:
        print(f"❌ AI analysis error: {e}")
        # Return properly structured error result with consistent scoring
        error_score = 10
        
        # Define weights for error case
        error_type_weights = {
            'portfolio': {'security': 0.10, 'performance': 0.30, 'seo': 0.15, 'mobile': 0.20, 'content': 0.05, 'uiux': 0.20},
            'landing-page': {'security': 0.15, 'performance': 0.20, 'seo': 0.25, 'mobile': 0.15, 'content': 0.05, 'uiux': 0.20},
            'search-engine': {'security': 0.25, 'performance': 0.40, 'seo': 0.05, 'mobile': 0.20, 'content': 0.05, 'uiux': 0.05},
            'e-commerce': {'security': 0.25, 'performance': 0.20, 'seo': 0.15, 'mobile': 0.15, 'content': 0.05, 'uiux': 0.20},
            'blog': {'security': 0.10, 'performance': 0.15, 'seo': 0.35, 'mobile': 0.20, 'content': 0.10, 'uiux': 0.10},
            'website': {'security': 0.15, 'performance': 0.20, 'seo': 0.20, 'mobile': 0.20, 'content': 0.10, 'uiux': 0.15},
        }
        
        error_weights = error_type_weights.get(website_type, error_type_weights['website'])
        
        # Distribute the error score proportionally across categories  
        error_breakdown = {}
        for category, weight in error_weights.items():
            contribution = round(error_score * weight, 1)
            error_breakdown[category] = {
                'score': 0, 
                'weight': int(weight * 100),
                'contribution': contribution
            }
        
        return {
            'score': error_score,
            'strengths': [],
            'improvements': [f"🚨 Analysis failed: {str(e)}"],
            'all_recommendations': [f"🚨 Analysis failed: {str(e)}"],
            'score_breakdown': {
                **error_breakdown,
                'calculation': {
                    'base_score': error_score,
                    'penalty_total': 0,
                    'final_score': error_score,
                    'verification': 'ERROR CASE'
                },
                'website_type': website_type,
                'critical_issues': 1,
                'major_issues': 0
            }
        }

def analyze_website_with_type(url: str, website_type: str = 'website'):
    """
    Analyze website with type-specific scoring criteria.
    Different website types have different priorities and expectations.
    """
    recommendations = []
    score = 0
    critical_issues = []
    major_issues = []
    minor_issues = []
    
    # Ensure URL has protocol
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    print(f"Analyzing {website_type}: {url}")
    
    # Define scoring weights based on website type
    type_weights = {
        'landing-page': {
            'conversion_focus': 0.3,    # High focus on conversion elements
            'seo': 0.2,                 # Lower SEO priority
            'speed': 0.25,              # High speed priority
            'mobile': 0.25,             # High mobile priority
            'expected_score_range': (60, 85)  # Landing pages should score well if optimized
        },
        'website': {
            'conversion_focus': 0.15,   # Moderate conversion focus
            'seo': 0.3,                 # High SEO priority
            'speed': 0.2,               # Moderate speed priority
            'mobile': 0.2,              # Moderate mobile priority
            'expected_score_range': (50, 80)  # General websites
        },
        'e-commerce': {
            'conversion_focus': 0.35,   # Highest conversion focus
            'seo': 0.25,                # High SEO priority
            'speed': 0.2,               # High speed priority (checkout flow)
            'mobile': 0.2,              # High mobile priority
            'expected_score_range': (65, 90)  # E-commerce should be well optimized
        },
        'search-engine': {
            'conversion_focus': 0.1,    # Low conversion focus
            'seo': 0.1,                 # Ironically low SEO needs
            'speed': 0.4,               # Extremely high speed priority
            'mobile': 0.4,              # Extremely high mobile priority
            'expected_score_range': (70, 95)  # Search engines are highly optimized
        },
        'blog': {
            'conversion_focus': 0.1,    # Low conversion focus
            'seo': 0.4,                 # Highest SEO priority
            'speed': 0.25,              # High speed priority
            'mobile': 0.25,             # High mobile priority
            'expected_score_range': (55, 85)  # Blogs vary widely
        },
        'portfolio': {
            'conversion_focus': 0.2,    # Moderate conversion focus
            'seo': 0.2,                 # Moderate SEO priority
            'speed': 0.3,               # High speed priority (visual content)
            'mobile': 0.3,              # High mobile priority
            'expected_score_range': (60, 85)  # Portfolios should look professional
        },
        'web-app': {
            'conversion_focus': 0.1,    # Low conversion focus
            'seo': 0.1,                 # Low SEO priority
            'speed': 0.4,               # Extremely high speed priority
            'mobile': 0.4,              # Extremely high mobile priority
            'expected_score_range': (65, 90)  # Web apps should be well built
        },
        'corporate': {
            'conversion_focus': 0.25,   # High conversion focus
            'seo': 0.3,                 # High SEO priority
            'speed': 0.225,             # Moderate speed priority
            'mobile': 0.225,            # Moderate mobile priority
            'expected_score_range': (55, 80)  # Corporate sites vary
        }
    }
    
    weights = type_weights.get(website_type, type_weights['website'])
    
    try:
        # Basic connectivity test with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        resp = requests.get(url, timeout=15, headers=headers, allow_redirects=True, verify=True)
        print(f"Response status: {resp.status_code}")
        print(f"Final URL after redirects: {resp.url}")
        
        # BASIC CONNECTIVITY (Required - if this fails, site gets very low score)
        if resp.status_code == 200:
            recommendations.append("✅ Website is accessible")
        elif resp.status_code in [301, 302, 303, 307, 308]:
            recommendations.append(f"⚠️ Website redirects (Status: {resp.status_code})")
        else:
            critical_issues.append(f"❌ CRITICAL: Website returned error status {resp.status_code}")
            return 5, critical_issues + major_issues + minor_issues + recommendations
            
    except requests.exceptions.SSLError as e:
        critical_issues.append("❌ CRITICAL: SSL Certificate error - website is not secure")
        print(f"SSL Error: {e}")
        return 3, critical_issues + major_issues + minor_issues + recommendations
    except requests.exceptions.Timeout:
        critical_issues.append("❌ CRITICAL: Website is too slow (15+ seconds) - users will leave")
        return 8, critical_issues + major_issues + minor_issues + recommendations
    except requests.exceptions.ConnectionError as e:
        critical_issues.append("❌ CRITICAL: Cannot connect to website - may be offline")
        print(f"Connection Error: {e}")
        return 2, critical_issues + major_issues + minor_issues + recommendations
    except Exception as e:
        critical_issues.append(f"❌ CRITICAL: Error accessing site: {str(e)}")
        print(f"General Error: {e}")
        return 5, critical_issues + major_issues + minor_issues + recommendations
    
    try:
        content = resp.text.lower()
        original_content = resp.text
        content_length = len(resp.text)
        response_time = resp.elapsed.total_seconds()
        
        print(f"Content length: {content_length} characters")
        print(f"Response time: {response_time:.2f}s")
        
        # Initialize scoring categories
        security_score = 0
        seo_score = 0
        performance_score = 0
        mobile_score = 0
        content_score = 0
        
        # SECURITY ANALYSIS
        if resp.url.startswith('https://'):
            security_score += 30
            recommendations.append("✅ Website uses HTTPS")
            
            # SSL Certificate validation
            try:
                import ssl
                import socket
                from urllib.parse import urlparse
                parsed_url = urlparse(resp.url)
                context = ssl.create_default_context()
                with socket.create_connection((parsed_url.hostname, 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=parsed_url.hostname) as ssock:
                        cert = ssock.getpeercert()
                        if cert:
                            security_score += 20
                            recommendations.append("✅ Valid SSL certificate")
            except Exception as ssl_error:
                major_issues.append("⚠️ MAJOR: Could not verify SSL certificate")
                print(f"SSL verification error: {ssl_error}")
        else:
            critical_issues.append("❌ CRITICAL: Website does NOT use HTTPS - major security risk")
            # No HTTPS is extremely bad for any site type
            security_score -= 30
        
        # SEO ANALYSIS (weight varies by site type)
        import re
        
        # Title Tag Analysis
        title_match = re.search(r'<title[^>]*>(.*?)</title>', original_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            if title and len(title) > 0:
                if 30 <= len(title) <= 60:
                    seo_score += 25
                    recommendations.append(f"✅ EXCELLENT: Perfect title length ({len(title)} chars)")
                elif 15 <= len(title) <= 80:
                    seo_score += 15
                    recommendations.append(f"✅ Good title tag ({len(title)} chars)")
                else:
                    if website_type in ['blog', 'website', 'corporate']:
                        major_issues.append(f"⚠️ MAJOR: Poor title length ({len(title)} chars) for {website_type}")
                        seo_score -= 10
                    else:
                        minor_issues.append(f"⚠️ Suboptimal title length ({len(title)} chars)")
                        seo_score += 5
            else:
                critical_issues.append("❌ CRITICAL: Title tag exists but is EMPTY")
                seo_score -= 20
        else:
            if website_type in ['blog', 'website', 'corporate', 'e-commerce']:
                critical_issues.append("❌ CRITICAL: NO title tag - terrible for SEO")
                seo_score -= 25
            else:
                major_issues.append("⚠️ MAJOR: Missing title tag")
                seo_score -= 15
        
        # Meta Description Analysis
        meta_desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']', original_content, re.IGNORECASE)
        if not meta_desc_match:
            meta_desc_match = re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']description["\']', original_content, re.IGNORECASE)
        
        if meta_desc_match:
            description = meta_desc_match.group(1).strip()
            if description and len(description) > 0:
                if 140 <= len(description) <= 160:
                    seo_score += 20
                    recommendations.append(f"✅ EXCELLENT: Perfect meta description")
                elif 120 <= len(description) <= 180:
                    seo_score += 15
                    recommendations.append(f"✅ Good meta description")
                else:
                    seo_score += 8
                    minor_issues.append(f"⚠️ Meta description length suboptimal")
            else:
                seo_score -= 10
                major_issues.append("⚠️ MAJOR: Meta description exists but is EMPTY")
        else:
            if website_type in ['blog', 'website', 'corporate', 'e-commerce']:
                critical_issues.append("❌ CRITICAL: NO meta description - terrible for SEO")
                seo_score -= 20
            else:
                minor_issues.append("⚠️ Missing meta description")
                seo_score -= 10
        
        # H1 Analysis
        h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', original_content, re.IGNORECASE | re.DOTALL)
        if h1_matches:
            if len(h1_matches) == 1:
                h1_text = re.sub(r'<[^>]+>', '', h1_matches[0]).strip()
                if len(h1_text) >= 10:
                    seo_score += 20
                    recommendations.append("✅ EXCELLENT: Perfect H1 structure")
                else:
                    seo_score += 10
                    minor_issues.append("⚠️ H1 is too short")
            else:
                major_issues.append(f"⚠️ MAJOR: Multiple H1 tags ({len(h1_matches)}) - confuses search engines")
                seo_score -= 15
        else:
            if website_type in ['blog', 'website', 'corporate']:
                critical_issues.append("❌ CRITICAL: NO H1 heading - terrible for SEO")
                seo_score -= 20
            else:
                major_issues.append("⚠️ MAJOR: Missing H1 heading")
                seo_score -= 10
        
        # PERFORMANCE ANALYSIS
        # Response time analysis (critical for all site types)
        if response_time > 3.0:
            critical_issues.append(f"❌ CRITICAL: Very slow response time ({response_time:.2f}s)")
            performance_score -= 30
        elif response_time > 1.5:
            major_issues.append(f"⚠️ MAJOR: Slow response time ({response_time:.2f}s)")
            performance_score -= 15
        elif response_time < 0.5:
            performance_score += 30
            recommendations.append(f"✅ EXCELLENT: Very fast response ({response_time:.2f}s)")
        elif response_time < 1.0:
            performance_score += 20
            recommendations.append(f"✅ Good response time ({response_time:.2f}s)")
        else:
            performance_score += 10
            recommendations.append(f"✅ Acceptable response time ({response_time:.2f}s)")
        
        # Page size analysis
        if content_length > 2000000:  # Over 2MB - very bad
            critical_issues.append(f"❌ CRITICAL: Extremely large page ({content_length:,} bytes)")
            performance_score -= 25
        elif content_length > 1000000:  # Over 1MB - bad
            major_issues.append(f"⚠️ MAJOR: Very large page ({content_length:,} bytes)")
            performance_score -= 15
        elif content_length > 500000:  # Over 500KB - concerning
            minor_issues.append(f"⚠️ Large page size ({content_length:,} bytes)")
            performance_score -= 8
        elif content_length < 10000:  # Under 10KB - suspiciously small
            if website_type not in ['search-engine']:
                minor_issues.append(f"⚠️ Very small page ({content_length:,} bytes) - might be incomplete")
                performance_score -= 5
        else:
            performance_score += 15
            recommendations.append(f"✅ Good page size ({content_length:,} bytes)")
        
        # MOBILE RESPONSIVENESS
        viewport_patterns = [
            r'<meta[^>]+name=["\']viewport["\']',
            r'<meta[^>]+content=["\'][^"\']*viewport[^"\']*["\']'
        ]
        viewport_found = any(re.search(pattern, original_content, re.IGNORECASE) for pattern in viewport_patterns)
        
        if viewport_found:
            mobile_score += 40
            recommendations.append("✅ EXCELLENT: Mobile-responsive (viewport meta tag)")
        else:
            critical_issues.append("❌ CRITICAL: NO viewport tag - broken on mobile")
            mobile_score -= 30
        
        # Responsive design indicators
        responsive_indicators = [
            r'@media[^{]*\([^)]*max-width[^)]*\)',
            r'@media[^{]*\([^)]*min-width[^)]*\)',
            r'bootstrap',
            r'responsive',
            r'mobile-first'
        ]
        responsive_found = sum(1 for pattern in responsive_indicators if re.search(pattern, content))
        if responsive_found >= 2:
            mobile_score += 10
            recommendations.append("✅ Good responsive design indicators")
        elif responsive_found >= 1:
            mobile_score += 5
            recommendations.append("✅ Some responsive design found")
        
        # CONTENT QUALITY
        word_count = len(re.findall(r'\b\w+\b', original_content))
        
        # Content expectations vary by site type
        if website_type == 'landing-page':
            if 100 <= word_count <= 800:
                content_score += 25
                recommendations.append(f"✅ EXCELLENT: Perfect landing page content length ({word_count} words)")
            elif word_count < 100:
                major_issues.append(f"⚠️ MAJOR: Too little content for landing page ({word_count} words)")
                content_score -= 15
            elif word_count > 1500:
                minor_issues.append(f"⚠️ Very long for landing page ({word_count} words)")
                content_score += 10
            else:
                content_score += 15
                recommendations.append(f"✅ Good content length ({word_count} words)")
        elif website_type == 'blog':
            if word_count >= 800:
                content_score += 25
                recommendations.append(f"✅ EXCELLENT: Great content volume for blog ({word_count} words)")
            elif word_count >= 400:
                content_score += 15
                recommendations.append(f"✅ Good content volume ({word_count} words)")
            else:
                major_issues.append(f"⚠️ MAJOR: Too little content for blog ({word_count} words)")
                content_score -= 10
        elif website_type == 'search-engine':
            # Search engines typically have minimal content
            if word_count < 200:
                content_score += 20
                recommendations.append("✅ EXCELLENT: Minimal content as expected for search engine")
            else:
                content_score += 10
                recommendations.append("✅ Content appropriate for search engine")
        else:
            # General website content expectations
            if word_count < 150:
                if website_type == 'portfolio':
                    content_score += 10
                    minor_issues.append(f"⚠️ Minimal content ({word_count} words) - consider adding descriptions")
                else:
                    major_issues.append(f"⚠️ MAJOR: Very little content ({word_count} words)")
                    content_score -= 15
            elif word_count >= 300:
                content_score += 20
                recommendations.append(f"✅ Good content volume ({word_count} words)")
            else:
                content_score += 10
                minor_issues.append(f"⚠️ Minimal content ({word_count} words)")
        
        # IMAGE OPTIMIZATION
        img_matches = re.findall(r'<img[^>]*>', original_content, re.IGNORECASE)
        images_with_alt = re.findall(r'<img[^>]+alt=["\'][^"\']*["\'][^>]*>', original_content, re.IGNORECASE)
        
        if img_matches:
            alt_ratio = len(images_with_alt) / len(img_matches)
            if alt_ratio >= 0.9:
                content_score += 15
                recommendations.append(f"✅ EXCELLENT: Image accessibility ({len(images_with_alt)}/{len(img_matches)} have alt text)")
            elif alt_ratio >= 0.7:
                content_score += 10
                recommendations.append(f"✅ Good image accessibility")
            else:
                major_issues.append(f"⚠️ MAJOR: Poor accessibility - only {len(images_with_alt)}/{len(img_matches)} images have alt text")
                content_score -= 10
        
        # CALCULATE FINAL SCORE BASED ON WEBSITE TYPE
        # Normalize scores to 0-100 scale for each category
        security_score = max(-20, min(100, security_score))
        seo_score = max(-50, min(100, seo_score))  
        performance_score = max(-50, min(100, performance_score))
        mobile_score = max(-50, min(100, mobile_score))
        content_score = max(-30, min(100, content_score))
        
        print(f"Raw scores - Security: {security_score}, SEO: {seo_score}, Performance: {performance_score}, Mobile: {mobile_score}, Content: {content_score}")
        
        # Apply type-specific weights
        if website_type == 'search-engine':
            final_score = (security_score * 0.2 + performance_score * 0.4 + mobile_score * 0.4)
        elif website_type == 'landing-page':
            final_score = (security_score * 0.15 + performance_score * 0.25 + mobile_score * 0.25 + content_score * 0.35)
        elif website_type == 'blog':
            final_score = (security_score * 0.1 + seo_score * 0.4 + performance_score * 0.25 + mobile_score * 0.15 + content_score * 0.1)
        elif website_type == 'e-commerce':
            final_score = (security_score * 0.25 + seo_score * 0.2 + performance_score * 0.25 + mobile_score * 0.2 + content_score * 0.1)
        elif website_type == 'portfolio':
            final_score = (security_score * 0.1 + seo_score * 0.15 + performance_score * 0.35 + mobile_score * 0.3 + content_score * 0.1)
        elif website_type == 'web-app':
            final_score = (security_score * 0.2 + performance_score * 0.4 + mobile_score * 0.3 + content_score * 0.1)
        elif website_type == 'corporate':
            final_score = (security_score * 0.2 + seo_score * 0.3 + performance_score * 0.2 + mobile_score * 0.2 + content_score * 0.1)
        else:  # 'website' default
            final_score = (security_score * 0.15 + seo_score * 0.3 + performance_score * 0.25 + mobile_score * 0.2 + content_score * 0.1)
        
        # Apply harsh penalties for critical issues
        critical_penalty = len(critical_issues) * 20  # Increased penalty
        major_penalty = len(major_issues) * 8
        minor_penalty = len(minor_issues) * 3
        
        final_score = final_score - critical_penalty - major_penalty - minor_penalty
        
        # Ensure realistic scoring with hard caps
        if len(critical_issues) >= 3:
            final_score = min(final_score, 25)  # Multiple critical issues = very bad site
        elif len(critical_issues) >= 2:
            final_score = min(final_score, 35)
        elif len(critical_issues) >= 1:
            final_score = min(final_score, 50)
        elif len(major_issues) >= 4:
            final_score = min(final_score, 55)
        elif len(major_issues) >= 2:
            final_score = min(final_score, 70)
        
        # Additional reality check - if site has basic problems, cap the score
        basic_problems = 0
        if not resp.url.startswith('https://'):
            basic_problems += 1
        if not viewport_found:
            basic_problems += 1  
        if not title_match or (title_match and not title_match.group(1).strip()):
            basic_problems += 1
        if response_time > 2.0:
            basic_problems += 1
        if content_length > 1000000:
            basic_problems += 1
            
        if basic_problems >= 3:
            final_score = min(final_score, 35)  # Sites with 3+ basic problems can't score well
        elif basic_problems >= 2:
            final_score = min(final_score, 55)
        
        final_score = max(0, min(100, final_score))
            
    except Exception as e:
        print(f"Error analyzing content: {e}")
        critical_issues.append(f"❌ CRITICAL: Error analyzing page content: {str(e)}")
        final_score = 15
    
    # Combine all recommendations in priority order
    all_recommendations = critical_issues + major_issues + recommendations + minor_issues
    
    print(f"Final audit score for {website_type}: {final_score:.0f}/100")
    print(f"Critical: {len(critical_issues)}, Major: {len(major_issues)}, Minor: {len(minor_issues)}")
    
    return int(final_score), all_recommendations

# Enhanced function that returns structured data with AI-powered analysis
def analyze_website_enhanced(url: str, website_type: str = 'website'):
    """
    Enhanced website analysis using AI-powered metrics and real performance data
    """
    print(f"🚀 Starting enhanced AI analysis for {url} ({website_type})")
    
    # Use AI-powered analysis which now returns properly structured data
    ai_result = ai_powered_analysis(url, website_type)
    
    # The AI analysis now returns properly categorized strengths and improvements
    if isinstance(ai_result, dict):
        return ai_result
    else:
        # Fallback for unexpected format
        return {
            'score': 10,
            'strengths': [],
            'improvements': ['🚨 Unexpected analysis format'],
            'all_recommendations': ['🚨 Unexpected analysis format'],
            'score_breakdown': {
                'security': {'score': 0, 'weight': 20},
                'performance': {'score': 0, 'weight': 25},
                'seo': {'score': 0, 'weight': 25},
                'mobile': {'score': 0, 'weight': 20},
                'content': {'score': 0, 'weight': 10},
                'website_type': website_type,
                'critical_issues': 1,
                'major_issues': 0
            }
        }

# Wrapper function to maintain compatibility
def analyze_website(url: str, website_type: str = 'website'):
    return analyze_website_with_type(url, website_type)

if __name__ == "__main__":
    print("Starting AArkboosted Audit API...")
    print("Database path:", DB_PATH)
    import uvicorn
    print("Starting uvicorn server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
