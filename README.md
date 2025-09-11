# AArkboosted Website Auditor

> Internal SEO audit tool for **ArkBoostedAds LLC** - Professional AI-powered website analysis and optimization platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18.0+-61DAFB.svg)](https://reactjs.org/)

## 🏢 About

This is an **internal tool** developed for **ArkBoostedAds LLC** to provide comprehensive website audits and SEO analysis for our clients. The tool delivers professional-grade reports with actionable insights across multiple performance categories.

## 🚀 Features

- **Comprehensive Analysis**: Security, Performance, SEO, Mobile, Content, and UI/UX evaluation
- **AI-Powered Scoring**: Advanced algorithms with website type-specific optimization
- **Real Performance Data**: Integration with Google PageSpeed Insights API
- **Professional Reports**: Export branded PDF reports with detailed recommendations
- **Academic Grading**: Standard A+ to F grading scale with transparent scoring

## 🏗️ Tech Stack

**Backend:**
- FastAPI + Uvicorn ASGI server
- SQLite database with structured storage
- BeautifulSoup for HTML parsing
- Google PageSpeed Insights integration

**Frontend:**
- React 18 with modern hooks
- Tailwind CSS for responsive design
- React Router for SPA navigation
- jsPDF for professional report generation

## 📦 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/ak23bar/AArkboosted-Audit-Tool.git
cd AArkboosted-Audit-Tool
```

2. **Backend Setup**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install fastapi uvicorn requests beautifulsoup4 python-multipart
python minimal_audit_api.py
```

3. **Frontend Setup** (in new terminal)
```bash
cd frontend
npm install
npm start
```

4. **Access the application**
- Frontend: http://localhost:3001
- API: http://localhost:8000

## 🎯 Usage

1. Enter website URL and select type (portfolio, landing-page, e-commerce, etc.)
2. Get comprehensive analysis with 6-category scoring breakdown
3. Review prioritized recommendations (Critical → Important → Optimization)
4. Export professional PDF reports for **ArkBoostedAds LLC** clients

## 📊 Scoring Categories

| Category | Weight | Focus |
|----------|--------|-------|
| **Security** | 10-25% | HTTPS, SSL, vulnerabilities |
| **Performance** | 20-40% | Core Web Vitals, loading speed |
| **SEO** | 5-35% | Meta tags, structured data |
| **Mobile** | 15-25% | Responsive design, viewport |
| **Content** | 5-10% | Quality, readability, structure |
| **UI/UX** | 5-20% | Design, navigation, accessibility |

*Weights adjust based on website type for accurate evaluation*

## 🔧 API Endpoints

```bash
POST /api/audits/          # Create new audit
GET  /api/audits/          # List all audits  
GET  /api/audits/{id}      # Get specific audit
DELETE /api/audits/{id}    # Delete audit
```

## 🛠️ Development

### Running Tests
```bash
# Backend tests
cd backend && python -m pytest

# Frontend tests  
cd frontend && npm test
```

### Building for Production
```bash
# Frontend build
cd frontend && npm run build

# Backend deployment
cd backend && uvicorn minimal_audit_api:app --host 0.0.0.0 --port 8000
```

## 📈 Website Type Optimization

- **Portfolio**: UI/UX focused (30%), performance emphasis
- **Landing Page**: SEO optimized (25%), conversion focused
- **E-commerce**: Security priority (25%), user experience
- **Blog**: Content quality (10%), SEO heavy (35%)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google PageSpeed Insights API for performance data
- BeautifulSoup for HTML parsing capabilities
- React community for modern UI patterns
- FastAPI for high-performance API framework

---

**Internal Tool for ArkBoostedAds LLC** | Developed by [Akbar Aman](https://github.com/ak23bar) | Professional Website Analysis for Client Success
