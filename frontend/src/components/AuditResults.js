import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeftIcon, DocumentArrowDownIcon } from '@heroicons/react/24/outline';
import { auditsAPI } from '../api';
import jsPDF from 'jspdf';

const AuditResults = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generatingPdf, setGeneratingPdf] = useState(false);

  const fetchAudit = useCallback(async () => {
    try {
      const response = await auditsAPI.get(id);
      setAudit(response);
    } catch (error) {
      setError('Failed to load audit results');
      console.error('Failed to fetch audit:', error);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchAudit();
  }, [fetchAudit]);

  const generatePDF = async () => {
    setGeneratingPdf(true);
    
    // Show loading indicator and defer PDF generation to next tick for better UX
    await new Promise(resolve => setTimeout(resolve, 50));
    
    try {
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      let yPosition = 30;

      // Helper function to ensure sections don't get cut off across pages
      const ensureSpaceForSection = (requiredHeight = 40) => {
        if (yPosition + requiredHeight > pageHeight - 30) {
          pdf.addPage();
          yPosition = 30;
        }
        return yPosition;
      };

      // Enhanced text cleaning function for PDFs (cached for better performance)
      const cleanTextForPdf = (() => {
        const cache = new Map();
        return (text) => {
          if (!text) return '';
          
          if (cache.has(text)) {
            return cache.get(text);
          }
          
          const cleaned = text
            // Remove emojis and problematic unicode
            .replace(/[\u{1F000}-\u{1F6FF}|\u{1F700}-\u{1F77F}|\u{1F780}-\u{1F7FF}|\u{1F800}-\u{1F8FF}|\u{2600}-\u{26FF}|\u{2700}-\u{27BF}|\u{1F900}-\u{1F9FF}|\u{1F1E6}-\u{1F1FF}]/gu, '')
            // Remove specific problematic emojis
            .replace(/[🚨⚠️🔧✅❌🏆📊🎯💡🔥🚪📱💻🌐🔒⚡📝🎨]/g, '')
            // Remove control characters that cause encoding issues
            .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '')
            // Fix common character encoding issues
            .replace(/['']/g, "'")
            .replace(/[""]/g, '"')
            .replace(/[–—]/g, '-')
            .replace(/…/g, '...')
            .replace(/•/g, '- ')
            // Remove problematic prefixes
            .replace(/^[\s•\-*✓✗×√🚨⚠️🔧]+/, '')
            // Clean header patterns
            .replace(/^(CRITICAL BUSINESS RISKS?|MAJOR GROWTH BLOCKERS?|OPTIMIZATION OPPORTUNITIES?):\s*/i, '')
            // Fix character spacing issues where every character is separated
            .replace(/(\b[a-zA-Z]\s){2,}[a-zA-Z]?\b/g, (match) => {
              // Remove spaces between single characters to form words
              return match.replace(/\s+/g, '');
            })
            // Normalize whitespace
            .replace(/\s+/g, ' ')
            .trim();
            
          cache.set(text, cleaned);
          return cleaned;
        };
      })();

      // Professional Header with Branding
      pdf.setFillColor(44, 82, 130); // AArkboosted blue
      pdf.rect(0, 0, pageWidth, 25, 'F');
      
      pdf.setFontSize(20);
      pdf.setTextColor(255, 255, 255);
      pdf.text('AArkboosted', 20, 16);
      
      pdf.setFontSize(12);
      pdf.setTextColor(200, 220, 255);
      pdf.text('Professional Website Audit Tool', pageWidth - 20, 16, { align: 'right' });
      
      yPosition = 45;
      
      // Results Header (matching frontend)
      pdf.setFontSize(20);
      pdf.setTextColor(44, 82, 130);
      pdf.text(`Results for ${audit.website_url}`, 20, yPosition);
      
      yPosition += 12;
      
      // Website details line (matching frontend)
      pdf.setFontSize(11);
      pdf.setTextColor(100, 100, 100);
      const websiteType = audit.website_type ? audit.website_type.replace('-', ' ') : 'website';
      const dateStr = new Date(audit.created_at || new Date()).toLocaleDateString();
      const reportMode = isAdminMode ? 'Admin Mode' : 'Client Mode';
      pdf.text(`Website Type: ${websiteType}    Date: ${dateStr}    ${reportMode}`, 20, yPosition);
      
      yPosition += 25;

      // Overall Grade Section (matching frontend layout)
      const gradeBoxHeight = 50;
      pdf.setDrawColor(200, 200, 200);
      pdf.setLineWidth(0.5);
      pdf.setFillColor(255, 255, 255);
      pdf.roundedRect(20, yPosition, pageWidth - 40, gradeBoxHeight, 8, 8, 'FD');
      
      // "Overall Grade" header
      pdf.setFontSize(14);
      pdf.setTextColor(100, 100, 100);
      pdf.text('Overall Grade', pageWidth / 2, yPosition + 15, { align: 'center' });
      
      // Grade pill background (rounded rectangle for grade)
      const gradeColor = getScoreColor(audit.score);
      const pillWidth = 80;
      const pillHeight = 20;
      const pillX = (pageWidth - pillWidth) / 2;
      const pillY = yPosition + 20;
      
      pdf.setFillColor(...gradeColor);
      pdf.setDrawColor(...gradeColor);
      pdf.roundedRect(pillX, pillY, pillWidth, pillHeight, 10, 10, 'FD');
      
      // Grade text inside pill
      pdf.setFontSize(16);
      pdf.setTextColor(255, 255, 255);
      pdf.text(`Grade ${getGrade(audit.score)}`, pageWidth / 2, pillY + 13, { align: 'center' });
      
      // Score below grade
      pdf.setFontSize(18);
      pdf.setTextColor(50, 50, 50);
      pdf.text(`${audit.score}/100`, pageWidth / 2, yPosition + 48, { align: 'center' });
      
      yPosition += gradeBoxHeight + 20;

      // Score Breakdown Section
      if (audit.score_breakdown) {
        pdf.setFontSize(18);
        pdf.setTextColor(40, 40, 40);
        pdf.text('Score Breakdown', 20, yPosition);
        yPosition += 15;
        
        const breakdown = audit.score_breakdown;
        const categories = [
          { name: 'Security', key: 'security', color: [220, 53, 69] },
          { name: 'Performance', key: 'performance', color: [40, 167, 69] },
          { name: 'SEO', key: 'seo', color: [0, 123, 255] },
          { name: 'Mobile', key: 'mobile', color: [255, 193, 7] },
          { name: 'Content', key: 'content', color: [108, 117, 125] },
          { name: 'UI/UX', key: 'uiux', color: [155, 39, 176] }
        ];

        categories.forEach((cat, idx) => {
          const data = breakdown[cat.key];
          if (data) {
            pdf.setFontSize(12);
            pdf.setTextColor(60, 60, 60);
            pdf.text(`${cat.name}:`, 25, yPosition);
            pdf.text(`${data.score}/100 (${data.weight}% weight)`, 80, yPosition);
            
            // Progress bar
            const barWidth = 80;
            const barHeight = 4;
            const barX = 25;
            const barY = yPosition + 3;
            
            // Background
            pdf.setFillColor(240, 240, 240);
            pdf.rect(barX, barY, barWidth, barHeight, 'F');
            
            // Fill
            pdf.setFillColor(...cat.color);
            pdf.rect(barX, barY, (data.score / 100) * barWidth, barHeight, 'F');
            
            yPosition += 12;
          }
        });
        
        yPosition += 10;
      }

      // AI-Powered Client Summary Section
      if (audit.client_summary) {
        if (yPosition > pageHeight - 80) {
          pdf.addPage();
          yPosition = 20;
        }
        
        pdf.setFontSize(16);
        pdf.setTextColor(123, 104, 238);
        pdf.text('AI-Powered Executive Summary', 20, yPosition);
        yPosition += 15;

        // Executive Summary
        if (audit.client_summary.executive_summary) {
          pdf.setFontSize(12);
          pdf.setTextColor(75, 85, 99);
          pdf.text('Executive Summary:', 25, yPosition);
          yPosition += 8;
          
          pdf.setFontSize(10);
          pdf.setTextColor(60, 60, 60);
          const cleanSummary = cleanTextForPdf(audit.client_summary.executive_summary);
          const summaryLines = pdf.splitTextToSize(cleanSummary, pageWidth - 60);
          summaryLines.forEach((line) => {
            if (yPosition > pageHeight - 20) {
              pdf.addPage();
              yPosition = 20;
            }
            pdf.text(line, 30, yPosition);
            yPosition += 5;
          });
          yPosition += 8;
        }

        // Key Metrics
        pdf.setFontSize(12);
        pdf.setTextColor(75, 85, 99);
        pdf.text('Performance Summary:', 25, yPosition);
        yPosition += 8;
        
        pdf.setFontSize(10);
        pdf.setTextColor(60, 60, 60);
        const metricsLines = [
          `Overall Grade: ${audit.client_summary.grade} (${audit.client_summary.status})`,
          `Critical Issues: ${audit.client_summary.critical_count}`,
          `Major Issues: ${audit.client_summary.major_count}`,
          `Total Issues: ${audit.client_summary.total_issues}`,
          `Website Platform: ${audit.client_summary.website_platform}`,
          ''
        ];

        metricsLines.forEach((line) => {
          if (yPosition > pageHeight - 20) {
            pdf.addPage();
            yPosition = 20;
          }
          pdf.text(line, 30, yPosition);
          yPosition += 6;
        });

        // Priority Actions
        if (audit.client_summary.priority_actions && audit.client_summary.priority_actions.length > 0) {
          // Ensure the entire Priority Actions section fits on one page
          const estimatedHeight = 20 + (audit.client_summary.priority_actions.length * 12);
          yPosition = ensureSpaceForSection(estimatedHeight);
          
          pdf.setFontSize(12);
          pdf.setTextColor(75, 85, 99);
          pdf.text('Priority Actions:', 25, yPosition);
          yPosition += 8;
          
          pdf.setFontSize(10);
          pdf.setTextColor(60, 60, 60);
          audit.client_summary.priority_actions.forEach((action, idx) => {
            if (yPosition > pageHeight - 20) {
              pdf.addPage();
              yPosition = 20;
            }
            const cleanAction = cleanTextForPdf(action);
            const lines = pdf.splitTextToSize(`${idx + 1}. ${cleanAction}`, pageWidth - 60);
            pdf.text(lines, 30, yPosition);
            yPosition += lines.length * 6;
          });
          yPosition += 5;
        }

        // Business Impact
        if (audit.client_summary.business_impact && audit.client_summary.business_impact.length > 0) {
          // Ensure the entire Business Impact section fits on one page
          const estimatedHeight = 20 + (audit.client_summary.business_impact.length * 12);
          yPosition = ensureSpaceForSection(estimatedHeight);
          
          pdf.setFontSize(12);
          pdf.setTextColor(75, 85, 99);
          pdf.text('Business Impact:', 25, yPosition);
          yPosition += 8;
          
          pdf.setFontSize(10);
          pdf.setTextColor(60, 60, 60);
          audit.client_summary.business_impact.forEach((impact) => {
            if (yPosition > pageHeight - 20) {
              pdf.addPage();
              yPosition = 20;
            }
            const cleanImpact = cleanTextForPdf(impact);
            const lines = pdf.splitTextToSize(`• ${cleanImpact}`, pageWidth - 60);
            pdf.text(lines, 30, yPosition);
            yPosition += lines.length * 6;
          });
          yPosition += 5;
        }

        // ROI Projection
        if (audit.client_summary.roi_projection) {
          pdf.setFontSize(12);
          pdf.setTextColor(75, 85, 99);
          pdf.text('ROI Projection:', 25, yPosition);
          yPosition += 8;
          
          pdf.setFontSize(10);
          pdf.setTextColor(60, 60, 60);
          const cleanROI = cleanTextForPdf(audit.client_summary.roi_projection);
          const roiLines = pdf.splitTextToSize(cleanROI, pageWidth - 60);
          roiLines.forEach((line) => {
            if (yPosition > pageHeight - 20) {
              pdf.addPage();
              yPosition = 20;
            }
            pdf.text(line, 30, yPosition);
            yPosition += 5;
          });
          yPosition += 8;
        }

        // Implementation Timeline
        if (audit.client_summary.timeline) {
          pdf.setFontSize(12);
          pdf.setTextColor(75, 85, 99);
          pdf.text('Implementation Timeline:', 25, yPosition);
          yPosition += 8;
          
          pdf.setFontSize(10);
          pdf.setTextColor(60, 60, 60);
          const cleanTimeline = cleanTextForPdf(audit.client_summary.timeline);
          const timelineLines = pdf.splitTextToSize(cleanTimeline, pageWidth - 60);
          timelineLines.forEach((line) => {
            if (yPosition > pageHeight - 20) {
              pdf.addPage();
              yPosition = 20;
            }
            pdf.text(line, 30, yPosition);
            yPosition += 5;
          });
          yPosition += 8;
        }

        // AArkboosted Package Recommendation
        if (audit.client_summary.recommended_package) {
          pdf.setFontSize(12);
          pdf.setTextColor(75, 85, 99);
          pdf.text('Recommended AArkboosted Package:', 25, yPosition);
          yPosition += 8;
          
          pdf.setFontSize(11);
          pdf.setTextColor(123, 104, 238);
          pdf.text(`${audit.client_summary.recommended_package} - ${audit.client_summary.package_price}`, 30, yPosition);
          yPosition += 8;
          
          if (audit.client_summary.package_justification) {
            pdf.setFontSize(10);
            pdf.setTextColor(60, 60, 60);
            const cleanJustification = cleanTextForPdf(audit.client_summary.package_justification);
            const justificationLines = pdf.splitTextToSize(cleanJustification, pageWidth - 60);
            justificationLines.forEach((line) => {
              if (yPosition > pageHeight - 20) {
                pdf.addPage();
                yPosition = 20;
              }
              pdf.text(line, 30, yPosition);
              yPosition += 5;
            });
          }
          yPosition += 10;
        }
        
        yPosition += 10;
      }

      // Strengths Section
      if (audit.strengths && audit.strengths.length > 0) {
        // Ensure the entire Strengths section fits on one page
        const estimatedHeight = 50 + (audit.strengths.length * 20);
        yPosition = ensureSpaceForSection(estimatedHeight);
        
        pdf.setFontSize(16);
        pdf.setTextColor(40, 167, 69);
        pdf.text('What\'s Working Excellently', 20, yPosition);
        yPosition += 12;

        audit.strengths.forEach((strength) => {
          if (yPosition > pageHeight - 20) {
            pdf.addPage();
            yPosition = 20;
          }
          
          pdf.setFontSize(10);
          pdf.setTextColor(60, 60, 60);
          // Use enhanced text cleaning function
          const cleanText = cleanTextForPdf(strength);
          const lines = pdf.splitTextToSize(`• ${cleanText}`, pageWidth - 50);
          pdf.text(lines, 25, yPosition);
          yPosition += lines.length * 5;
        });
        
        yPosition += 15;
      }

      // Improvements Section
      if (audit.improvements && audit.improvements.length > 0) {
        // Ensure the entire Improvements section fits on one page
        const estimatedHeight = 50 + (audit.improvements.length * 20);
        yPosition = ensureSpaceForSection(estimatedHeight);
        
        pdf.setFontSize(16);
        pdf.setTextColor(220, 53, 69);
        pdf.text('Priority Improvement Areas', 20, yPosition);
        yPosition += 12;

        audit.improvements.forEach((improvement) => {
          if (yPosition > pageHeight - 20) {
            pdf.addPage();
            yPosition = 20;
          }
          
          // Use enhanced text cleaning function and skip empty items
          const cleanText = cleanTextForPdf(improvement);
          if (!cleanText || cleanText.trim() === '' || cleanText.trim() === '-') {
            return; // Skip empty or whitespace-only improvements
          }
          
          pdf.setFontSize(10);
          pdf.setTextColor(60, 60, 60);
          
          // Make improvements more concise for professional appearance
          let displayText = cleanText;
          
          // Truncate very long descriptions and add summary
          if (displayText.length > 150) {
            // Find a good break point
            const breakPoint = displayText.substring(0, 150).lastIndexOf(' ');
            displayText = displayText.substring(0, breakPoint > 100 ? breakPoint : 150) + '...';
          }
          
          // Ensure proper bullet point formatting
          const lines = pdf.splitTextToSize(`• ${displayText}`, pageWidth - 50);
          pdf.text(lines, 25, yPosition);
          yPosition += lines.length * 5;
        });
      }

      // Professional Footer
      const footerY = pageHeight - 20;
      pdf.setFillColor(44, 82, 130);
      pdf.rect(0, footerY - 5, pageWidth, 25, 'F');
      
      pdf.setFontSize(10);
      pdf.setTextColor(255, 255, 255);
      pdf.text('AArkboosted Website Audit Tool', 20, footerY + 5);
      
      pdf.setFontSize(8);
      pdf.setTextColor(200, 220, 255);
      pdf.text('Professional website analysis and optimization recommendations', 20, footerY + 12);
      
      pdf.setFontSize(10);
      pdf.setTextColor(255, 255, 255);
      pdf.text('Arkboosted LLC - https://arkboostedads.com', pageWidth - 20, footerY + 8, { align: 'right' });

      // Save the PDF
      const fileName = `audit-report-${audit.website_url.replace(/[^a-zA-Z0-9]/g, '-')}-${new Date().toISOString().split('T')[0]}.pdf`;
      pdf.save(fileName);
      
    } catch (error) {
      console.error('Error generating PDF:', error);
      alert('Failed to generate PDF report');
    } finally {
      setGeneratingPdf(false);
    }
  };

  const getScoreColor = (score) => {
    // Return RGB arrays for PDF colors
    if (score >= 90) return [34, 139, 34];    // Forest green for excellent
    if (score >= 80) return [0, 128, 0];      // Green for good
    if (score >= 70) return [255, 165, 0];    // Orange for fair
    if (score >= 60) return [255, 69, 0];     // Red-orange for poor
    return [220, 53, 69];                     // Red for failing
  };

  const getGradeColor = (score) => {
    // Academic grading colors
    if (score >= 93) return 'text-emerald-800 bg-emerald-100 border-emerald-300';  // A+ 
    if (score >= 87) return 'text-green-800 bg-green-100 border-green-300';        // A
    if (score >= 80) return 'text-lime-800 bg-lime-100 border-lime-300';           // A-
    if (score >= 73) return 'text-blue-800 bg-blue-100 border-blue-300';           // B
    if (score >= 67) return 'text-yellow-800 bg-yellow-100 border-yellow-300';     // C
    if (score >= 60) return 'text-orange-800 bg-orange-100 border-orange-300';     // D
    return 'text-red-800 bg-red-100 border-red-300';                              // F
  };

  const getGrade = (score) => {
    // Academic grading scale: F, D, C, B, A-, A+
    
    if (score >= 93) return 'A+';  // Exceptional quality (97-100)
    if (score >= 87) return 'A';   // Excellent quality (87-92)
    if (score >= 80) return 'A-';  // Very good quality (80-86)
    if (score >= 73) return 'B';   // Good quality (73-79)
    if (score >= 67) return 'C';   // Average quality (67-72)
    if (score >= 60) return 'D';   // Below average (60-66)
    return 'F';                    // Failing quality (0-59)
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading audit results...</p>
        </div>
      </div>
    );
  }

  if (error || !audit) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Error Loading Audit</h2>
          <p className="text-gray-600">{error || 'Audit not found'}</p>
          <button
            onClick={() => navigate('/')}
            className="mt-4 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            Back to Audits
          </button>
        </div>
      </div>
    );
  }

  // Use explicit report_mode from API response instead of detecting from structure
  const isAdminMode = audit?.report_mode === 'admin';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <img 
                src="/AAboosted-logo.png" 
                alt="AArkboosted" 
                className="h-8 w-auto mr-3"
              />
              <h1 className="text-2xl font-bold text-gray-900">
                Audit Results
              </h1>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={generatePDF}
                disabled={generatingPdf}
                className="inline-flex items-center px-4 py-2 border border-blue-300 text-sm font-medium rounded-md text-blue-700 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                <DocumentArrowDownIcon className="h-4 w-4 mr-2" />
                {generatingPdf ? 'Generating...' : 'Export Report'}
              </button>
              <button
                onClick={() => navigate('/')}
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <ArrowLeftIcon className="h-4 w-4 mr-2" />
                Back to Dashboard
              </button>
            </div>
          </div>
        </div>
      </header>
      
      <div className="py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Audit Content */}
          <div className="mb-8">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-3xl font-bold text-gray-900">Results for {audit.website_url}</h2>
                <div className="mt-2 flex items-center space-x-4">
                  <span className="text-gray-600">
                    Website Type: <span className="font-medium capitalize">{audit.website_type.replace('-', ' ')}</span>
                  </span>
                  <span className="text-gray-600">
                    Date: <span className="font-medium">{new Date(audit.created_at).toLocaleDateString()}</span>
                  </span>
                  {/* Report Mode Indicator - infer from data structure */}
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    isAdminMode ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                  }`}>
                    {isAdminMode ? '👨‍💼 Admin Mode' : '🎯 Client Mode'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Overall Grade */}
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <div className="text-center">
              <div className="mb-4">
                <span className="text-lg text-gray-600">Overall Grade</span>
              </div>
              <div className={`inline-flex items-center px-8 py-4 rounded-full text-4xl font-bold ${getGradeColor(audit.score || 0)}`}>
                Grade {getGrade(audit.score || 0)}
              </div>
              <div className="mt-4">
                <span className="text-2xl font-semibold text-gray-900">{audit.score || 0}/100</span>
              </div>
            </div>
          </div>

          {/* Score Breakdown */}
          {audit.score_breakdown && (
            <div className="bg-white rounded-lg shadow overflow-hidden mb-8">
              <div className="bg-gradient-to-r from-blue-500 to-indigo-600 px-6 py-4">
                <h2 className="text-xl font-bold text-white flex items-center">
                  <span className="text-2xl mr-3">📊</span>
                  Score Breakdown
                </h2>
                <p className="text-blue-100 text-sm mt-1">
                  Detailed scoring breakdown by category for {audit.score_breakdown.website_type.replace('-', ' ')} website
                </p>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {[
                    { name: 'Security', key: 'security', icon: '🔒', color: 'red' },
                    { name: 'Performance', key: 'performance', icon: '⚡', color: 'green' },
                    { name: 'SEO', key: 'seo', icon: '🎯', color: 'blue' },
                    { name: 'Mobile', key: 'mobile', icon: '📱', color: 'yellow' },
                    { name: 'Content', key: 'content', icon: '📝', color: 'gray' },
                    { name: 'UI/UX', key: 'uiux', icon: '🎨', color: 'purple' }
                  ].map((category) => {
                    const data = audit.score_breakdown[category.key];
                    if (!data) return null;
                    
                    return (
                      <div key={category.key} className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center">
                            <span className="text-xl mr-2">{category.icon}</span>
                            <span className="font-medium text-gray-900">{category.name}</span>
                          </div>
                          <span className="text-sm text-gray-600">{data.weight}% weight</span>
                        </div>
                        
                        <div className="mb-2">
                          <div className="flex justify-between items-center">
                            <span className="text-2xl font-bold text-gray-900">{data.score}/100</span>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              data.score >= 80 ? 'bg-green-100 text-green-800' :
                              data.score >= 60 ? 'bg-yellow-100 text-yellow-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {data.score >= 80 ? 'Excellent' : data.score >= 60 ? 'Good' : 'Needs Work'}
                            </span>
                          </div>
                        </div>
                        
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full transition-all duration-300 ${
                              data.score >= 80 ? 'bg-green-500' :
                              data.score >= 60 ? 'bg-yellow-500' :
                              'bg-red-500'
                            }`}
                            style={{ width: `${Math.min(100, Math.max(0, data.score))}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                
                {/* Issues Summary */}
                <div className="mt-6 pt-6 border-t border-gray-200">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="flex items-center">
                      <span className="text-red-600 text-lg mr-2">🚨</span>
                      <span className="text-sm text-gray-600">
                        <span className="font-medium text-red-600">{audit.score_breakdown.critical_issues}</span> Critical Issues
                      </span>
                    </div>
                    <div className="flex items-center">
                      <span className="text-orange-600 text-lg mr-2">⚠️</span>
                      <span className="text-sm text-gray-600">
                        <span className="font-medium text-orange-600">{audit.score_breakdown.major_issues}</span> Major Issues
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* AI-Powered Client Summary */}
          {audit.client_summary && (
            <div className="bg-white rounded-lg shadow overflow-hidden mb-8">
              <div className="bg-gradient-to-r from-purple-500 to-pink-600 px-6 py-4">
                <h2 className="text-xl font-bold text-white flex items-center">
                  <span className="text-2xl mr-3">🤖</span>
                  AI-Powered Executive Summary
                </h2>
                <p className="text-purple-100 text-sm mt-1">
                  Personalized business intelligence and strategic recommendations for {audit.client_summary.business_name}
                </p>
              </div>
              <div className="p-6">
                
                {/* Executive Summary */}
                <div className="mb-6 bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg p-6 border-l-4 border-purple-400">
                  <div className="whitespace-pre-line text-gray-800 leading-relaxed">
                    {audit.client_summary.executive_summary}
                  </div>
                </div>

                {/* Key Metrics Overview */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                  <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-blue-800">{audit.client_summary.grade}</div>
                    <div className="text-sm text-blue-600 font-medium">{audit.client_summary.status}</div>
                  </div>
                  <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-red-800">{audit.client_summary.critical_count}</div>
                    <div className="text-sm text-red-600 font-medium">Critical Issues</div>
                  </div>
                  <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-orange-800">{audit.client_summary.major_count}</div>
                    <div className="text-sm text-orange-600 font-medium">Major Issues</div>
                  </div>
                  <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-gray-800">{audit.client_summary.total_issues}</div>
                    <div className="text-sm text-gray-600 font-medium">Total Issues</div>
                  </div>
                </div>

                {/* Business Impact */}
                {audit.client_summary.business_impact && audit.client_summary.business_impact.length > 0 && (
                  <div className="mb-6 bg-blue-50 rounded-lg p-4 border border-blue-200">
                    <h4 className="font-semibold text-blue-800 mb-3 flex items-center">
                      <span className="mr-2">💼</span>
                      Business Impact Assessment
                    </h4>
                    <ul className="space-y-2">
                      {audit.client_summary.business_impact.map((impact, idx) => (
                        <li key={idx} className="text-blue-700 text-sm flex items-start">
                          <span className="mr-2 text-blue-500">•</span>
                          <span className="whitespace-pre-line">{impact}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* ROI Projection & Timeline */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  {audit.client_summary.roi_projection && (
                    <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                      <h4 className="font-semibold text-green-800 mb-3 flex items-center">
                        <span className="mr-2">📈</span>
                        ROI Projection
                      </h4>
                      <p className="text-green-700 text-sm whitespace-pre-line">
                        {audit.client_summary.roi_projection}
                      </p>
                    </div>
                  )}
                  
                  {audit.client_summary.timeline && (
                    <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                      <h4 className="font-semibold text-purple-800 mb-3 flex items-center">
                        <span className="mr-2">⏰</span>
                        Implementation Timeline
                      </h4>
                      <p className="text-purple-700 text-sm whitespace-pre-line">
                        {audit.client_summary.timeline}
                      </p>
                    </div>
                  )}
                </div>

                {/* AArkboosted Package Recommendation */}
                {audit.client_summary.recommended_package && (
                  <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg p-6 border-2 border-indigo-200">
                    <h4 className="font-bold text-indigo-800 mb-2 flex items-center text-lg">
                      <span className="mr-2">🚀</span>
                      Recommended AArkboosted Package
                    </h4>
                    <div className="mb-3">
                      <span className="inline-block bg-indigo-100 text-indigo-800 px-3 py-1 rounded-full text-sm font-medium">
                        {audit.client_summary.recommended_package}
                      </span>
                      <span className="ml-3 text-lg font-bold text-indigo-900">
                        {audit.client_summary.package_price}
                      </span>
                    </div>
                    {audit.client_summary.package_justification && (
                      <div className="text-indigo-700 text-sm whitespace-pre-line leading-relaxed">
                        {audit.client_summary.package_justification}
                      </div>
                    )}
                    <div className="mt-4 pt-4 border-t border-indigo-200">
                      <p className="text-indigo-600 text-xs italic">
                        Platform detected: {audit.client_summary.website_platform}
                      </p>
                    </div>
                  </div>
                )}

              </div>
            </div>
          )}

          {/* Structured Results with Priority-Based Organization */}
          <div className="space-y-6">
            {/* What's Working Well - Organized by Impact */}
            {audit.strengths && audit.strengths.length > 0 && (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="bg-gradient-to-r from-green-500 to-emerald-600 px-6 py-4">
                  <h2 className="text-xl font-bold text-white flex items-center">
                    <span className="text-2xl mr-3">🏆</span>
                    What's Working Excellently
                  </h2>
                  <p className="text-green-100 text-sm mt-1">
                    These elements are performing at a high level and contributing to your site's success
                  </p>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    {audit.strengths.map((strength, idx) => {
                      // Determine the icon and styling based on content
                      let iconClass = "";
                      let textClass = "text-gray-700";
                      let bgClass = "bg-green-50";
                      
                      if (strength.includes('🏆')) {
                        iconClass = "text-yellow-600";
                        bgClass = "bg-yellow-50 border-l-4 border-yellow-400";
                        textClass = "text-yellow-800 font-medium";
                      } else if (strength.includes('✅')) {
                        iconClass = "text-green-600";
                        bgClass = "bg-green-50 border-l-4 border-green-400";
                        textClass = "text-green-800";
                      }
                      
                      return (
                        <div key={idx} className={`p-3 rounded-lg ${bgClass}`}>
                          <div className="flex items-start">
                            <div className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center mr-3 mt-0.5 ${iconClass}`}>
                              {strength.includes('🏆') ? '🏆' : '✅'}
                            </div>
                            <span className={`leading-relaxed ${textClass}`}>
                              {strength.replace(/^🏆\s*/, '').replace(/^✅\s*/, '')}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Areas for Improvement - Organized by Priority */}
            {audit.improvements && audit.improvements.length > 0 && (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="bg-gradient-to-r from-orange-500 to-red-600 px-6 py-4">
                  <h2 className="text-xl font-bold text-white flex items-center">
                    <span className="text-2xl mr-3">🎯</span>
                    Priority Improvement Areas
                  </h2>
                  <p className="text-orange-100 text-sm mt-1">
                    Organized by impact - address critical issues first, then work through optimizations
                  </p>
                </div>
                <div className="p-6">
                  {(() => {
                    // Parse improvements into structured categories
                    const categories = {
                      critical: { title: 'Critical Business Risks', items: [], emoji: '🚨', color: 'red' },
                      major: { title: 'Major Growth Blockers', items: [], emoji: '⚠️', color: 'orange' },
                      optimization: { title: 'Optimization Opportunities', items: [], emoji: '🔧', color: 'blue' }
                    };
                    
                    let currentCategory = null;
                    
                    audit.improvements.forEach(item => {
                      // Handle both admin and client mode header formats
                      if (item.includes('🚨 CRITICAL BUSINESS RISKS:') || 
                          item.includes('🚨 URGENT:') || 
                          item.includes('🚨 Critical Business Risks')) {
                        currentCategory = 'critical';
                      } else if (item.includes('⚠️ MAJOR GROWTH BLOCKERS:') || 
                                 item.includes('⚠️ MAJOR:') ||
                                 item.includes('⚠️ Major Growth Blockers')) {
                        currentCategory = 'major';
                      } else if (item.includes('🔧 OPTIMIZATION OPPORTUNITIES:') || 
                                 item.includes('🔧 OPTIMIZATION:') ||
                                 item.includes('🔧 Optimization Opportunities')) {
                        currentCategory = 'optimization';
                      } else if (currentCategory && 
                                 !item.includes('🚨 CRITICAL BUSINESS RISKS:') &&
                                 !item.includes('⚠️ MAJOR GROWTH BLOCKERS:') &&
                                 !item.includes('🔧 OPTIMIZATION OPPORTUNITIES:') &&
                                 !item.includes('🚨 URGENT:') &&
                                 !item.includes('⚠️ MAJOR:') &&
                                 !item.includes('🔧 OPTIMIZATION:')) {
                        // This is an actual improvement item, not a header
                        categories[currentCategory].items.push(item);
                      }
                    });
                    
                    // Fallback: If no items were categorized (client mode without headers), 
                    // treat all improvements as critical issues
                    const totalCategorizedItems = Object.values(categories).reduce((sum, cat) => sum + cat.items.length, 0);
                    if (totalCategorizedItems === 0 && audit.improvements.length > 0) {
                      // Put all improvements in critical category, skipping obvious header-like items
                      audit.improvements.forEach(item => {
                        // Skip items that look like headers but don't match our patterns
                        if (!item.includes('🚨 URGENT:') && !item.includes('Issues Requiring') && item.trim().length > 10) {
                          categories.critical.items.push(item);
                        }
                      });
                    }
                    
                    return (
                      <div className="space-y-6">
                        {Object.entries(categories).map(([key, category]) => (
                          category.items.length > 0 && (
                            <div key={key} className={`border rounded-lg overflow-hidden ${
                              category.color === 'red' ? 'border-red-200' :
                              category.color === 'orange' ? 'border-orange-200' : 'border-blue-200'
                            }`}>
                              <div className={`px-4 py-3 ${
                                category.color === 'red' ? 'bg-red-50' :
                                category.color === 'orange' ? 'bg-orange-50' : 'bg-blue-50'
                              }`}>
                                <h3 className={`font-semibold flex items-center ${
                                  category.color === 'red' ? 'text-red-800' :
                                  category.color === 'orange' ? 'text-orange-800' : 'text-blue-800'
                                }`}>
                                  <span className="text-lg mr-2">{category.emoji}</span>
                                  {category.title}
                                  <span className={`ml-2 px-2 py-1 rounded-full text-xs ${
                                    category.color === 'red' ? 'bg-red-200 text-red-700' :
                                    category.color === 'orange' ? 'bg-orange-200 text-orange-700' : 'bg-blue-200 text-blue-700'
                                  }`}>
                                    {category.items.length}
                                  </span>
                                </h3>
                              </div>
                              <div className="p-4 space-y-3">
                                {category.items.map((item, idx) => (
                                  <div key={idx} className={`p-3 rounded border-l-4 ${
                                    category.color === 'red' ? 'bg-red-25 border-red-400' :
                                    category.color === 'orange' ? 'bg-orange-25 border-orange-400' : 'bg-blue-25 border-blue-400'
                                  }`}>
                                    <p className={`text-sm leading-relaxed ${
                                      category.color === 'red' ? 'text-red-700' :
                                      category.color === 'orange' ? 'text-orange-700' : 'text-blue-700'
                                    }`}>
                                      {item.replace(/^🚨\s*/, '').replace(/^⚠️\s*/, '').replace(/^🔧\s*/, '')}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )
                        ))}
                      </div>
                    );
                  })()}
                </div>
              </div>
            )}

            {/* Fallback to old recommendations if no structured data */}
            {(!audit.strengths || audit.strengths.length === 0) && (!audit.improvements || audit.improvements.length === 0) && 
             audit.recommendations && audit.recommendations.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">All Recommendations</h2>
                <ul className="space-y-2">
                  {audit.recommendations.map((recommendation, idx) => (
                    <li key={idx} className="flex items-start">
                      <span className="flex-shrink-0 w-2 h-2 bg-blue-600 rounded-full mt-2 mr-3"></span>
                      <span className="text-gray-700">{recommendation}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuditResults;