import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeftIcon, DocumentArrowDownIcon } from '@heroicons/react/24/outline';
import { auditsAPI } from '../api';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

const AuditResults = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generatingPdf, setGeneratingPdf] = useState(false);

  useEffect(() => {
    fetchAudit();
  }, [id]);

  const fetchAudit = async () => {
    try {
      const response = await auditsAPI.get(id);
      setAudit(response);
    } catch (error) {
      setError('Failed to load audit results');
      console.error('Failed to fetch audit:', error);
    } finally {
      setLoading(false);
    }
  };

  const generatePDF = async () => {
    setGeneratingPdf(true);
    try {
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      let yPosition = 30;

      // Enhanced text cleaning function for PDFs
      const cleanTextForPdf = (text) => {
        return text
          // Remove ALL emojis and symbols
          .replace(/[\u{1F000}-\u{1F6FF}|\u{1F700}-\u{1F77F}|\u{1F780}-\u{1F7FF}|\u{1F800}-\u{1F8FF}|\u{2600}-\u{26FF}|\u{2700}-\u{27BF}|\u{1F900}-\u{1F9FF}|\u{1F1E6}-\u{1F1FF}]/gu, '')
          // Remove specific problematic symbols
          .replace(/[þÞøØæÆåÅñÑ¿¡]/g, '')
          // Remove bullet symbols and emoji-like characters
          .replace(/[🔥💡⚠️❌✅📊🎯🚨🤖]/g, '')
          // Remove various bullet points and prefixes
          .replace(/^[\s•\-\*✓✗×√]+/, '')
          // Clean up multiple spaces
          .replace(/\s+/g, ' ')
          .trim();
      };

      // Header
      pdf.setFontSize(24);
      pdf.setTextColor(44, 82, 130);
      pdf.text('Website Audit Report', pageWidth / 2, yPosition, { align: 'center' });
      
      yPosition += 15;
      pdf.setFontSize(16);
      pdf.setTextColor(100, 100, 100);
      pdf.text(audit.website_url, pageWidth / 2, yPosition, { align: 'center' });
      
      yPosition += 10;
      pdf.setFontSize(12);
      pdf.text(`Generated on ${new Date().toLocaleDateString()}`, pageWidth / 2, yPosition, { align: 'center' });
      
      yPosition += 20;

      // Score Box
      pdf.setDrawColor(200, 200, 200);
      pdf.setFillColor(248, 249, 250);
      pdf.roundedRect(20, yPosition, pageWidth - 40, 30, 3, 3, 'FD');
      
      pdf.setFontSize(36);
      pdf.setTextColor(220, 53, 69);
      pdf.text(`${audit.score}/100`, pageWidth / 2, yPosition + 15, { align: 'center' });
      
      pdf.setFontSize(18);
      pdf.text(`Grade ${getGrade(audit.score)}`, pageWidth / 2, yPosition + 25, { align: 'center' });
      
      yPosition += 45;

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

      // Strengths Section
      if (audit.strengths && audit.strengths.length > 0) {
        if (yPosition > pageHeight - 50) {
          pdf.addPage();
          yPosition = 20;
        }
        
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
        if (yPosition > pageHeight - 50) {
          pdf.addPage();
          yPosition = 20;
        }
        
        pdf.setFontSize(16);
        pdf.setTextColor(220, 53, 69);
        pdf.text('Priority Improvement Areas', 20, yPosition);
        yPosition += 12;

        audit.improvements.forEach((improvement) => {
          if (yPosition > pageHeight - 20) {
            pdf.addPage();
            yPosition = 20;
          }
          
          pdf.setFontSize(10);
          pdf.setTextColor(60, 60, 60);
          // Use enhanced text cleaning function
          const cleanText = cleanTextForPdf(improvement);
          const lines = pdf.splitTextToSize(`• ${cleanText}`, pageWidth - 50);
          pdf.text(lines, 25, yPosition);
          yPosition += lines.length * 5;
        });
      }

      // Footer
      const footerY = pageHeight - 15;
      pdf.setFontSize(8);
      pdf.setTextColor(150, 150, 150);
      pdf.text('Report generated by AArkboosted Website Audit Tool - https://aarkboosted.com', pageWidth / 2, footerY, { align: 'center' });

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
            <h2 className="text-3xl font-bold text-gray-900">Results for {audit.website_url}</h2>
            <p className="mt-2 text-gray-600">
              Website Type: <span className="font-medium capitalize">{audit.website_type.replace('-', ' ')}</span> | 
              Date: <span className="font-medium">{new Date(audit.created_at).toLocaleDateString()}</span>
            </p>
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
                  <div className="space-y-4">
                    {audit.improvements.map((improvement, idx) => {
                      // Determine priority and styling based on content
                      let priority = "";
                      let iconClass = "";
                      let textClass = "text-gray-700";
                      let bgClass = "bg-gray-50";
                      let borderClass = "border-gray-300";
                      
                      if (improvement.includes('🚨')) {
                        priority = "CRITICAL";
                        iconClass = "text-red-600";
                        bgClass = "bg-red-50 border-l-4 border-red-500";
                        textClass = "text-red-800 font-semibold";
                        borderClass = "border-red-500";
                      } else if (improvement.includes('⚠️')) {
                        priority = "IMPORTANT";
                        iconClass = "text-orange-600";
                        bgClass = "bg-orange-50 border-l-4 border-orange-400";
                        textClass = "text-orange-800 font-medium";
                        borderClass = "border-orange-400";
                      } else if (improvement.includes('🔧')) {
                        priority = "OPTIMIZATION";
                        iconClass = "text-blue-600";
                        bgClass = "bg-blue-50 border-l-4 border-blue-400";
                        textClass = "text-blue-800";
                        borderClass = "border-blue-400";
                      }
                      
                      return (
                        <div key={idx} className={`p-4 rounded-lg ${bgClass}`}>
                          <div className="flex items-start">
                            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center mr-3 ${iconClass}`}>
                              {improvement.includes('🚨') ? '🚨' : improvement.includes('⚠️') ? '⚠️' : '🔧'}
                            </div>
                            <div className="flex-1">
                              {priority && (
                                <div className={`inline-block px-2 py-1 rounded text-xs font-medium mb-2 ${
                                  priority === 'CRITICAL' ? 'bg-red-200 text-red-800' :
                                  priority === 'IMPORTANT' ? 'bg-orange-200 text-orange-800' :
                                  'bg-blue-200 text-blue-800'
                                }`}>
                                  {priority}
                                </div>
                              )}
                              <p className={`leading-relaxed ${textClass}`}>
                                {improvement.replace(/^🚨\s*/, '').replace(/^⚠️\s*/, '').replace(/^🔧\s*/, '')}
                              </p>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
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