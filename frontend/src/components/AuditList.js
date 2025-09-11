import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { EyeIcon, PlusIcon, TrashIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { auditsAPI } from '../api';

const AuditList = () => {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingIds, setDeletingIds] = useState(new Set());
  const navigate = useNavigate();

  useEffect(() => {
    fetchAudits();
  }, []);

  const fetchAudits = async () => {
    try {
      const response = await auditsAPI.list();
      setAudits(response || []);
    } catch (error) {
      console.error('Failed to fetch audits:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAudit = async (auditId, websiteUrl) => {
    if (!window.confirm(`Are you sure you want to delete the audit for "${websiteUrl}"?`)) {
      return;
    }

    setDeletingIds(prev => new Set([...prev, auditId]));
    try {
      await auditsAPI.delete(auditId);
      toast.success('Audit deleted successfully');
      // Remove the deleted audit from the list
      setAudits(prevAudits => prevAudits.filter(audit => audit.id !== auditId));
    } catch (error) {
      console.error('Failed to delete audit:', error);
      toast.error('Failed to delete audit. Please try again.');
    } finally {
      setDeletingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(auditId);
        return newSet;
      });
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
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading audits...</span>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="sm:flex sm:items-center sm:justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Website Audits</h1>
          <p className="mt-2 text-sm text-gray-700">
            Manage and review your website audit reports
          </p>
        </div>
      </div>

      {/* Audits list */}
      {audits.length === 0 ? (
        <div className="text-center py-12">
          <div className="mx-auto h-24 w-24 bg-gray-100 rounded-full flex items-center justify-center">
            <PlusIcon className="h-12 w-12 text-gray-400" />
          </div>
          <h3 className="mt-4 text-lg font-medium text-gray-900">No audits yet</h3>
          <p className="mt-2 text-sm text-gray-500">
            Get started by creating your first website audit
          </p>
          <div className="mt-6">
            <button
              onClick={() => navigate('/new-audit')}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              <PlusIcon className="h-5 w-5 mr-2" />
              Create First Audit
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          <ul className="divide-y divide-gray-200">
            {audits.map((audit) => (
              <li key={audit.id}>
                <div className="px-4 py-4 flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="flex-shrink-0">
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getGradeColor(audit.score || 0)}`}>
                        Grade {getGrade(audit.score || 0)}
                      </span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {audit.website_url}
                      </p>
                      <p className="text-sm text-gray-500">
                        Score: {audit.score || 0}/100
                      </p>
                      <p className="text-xs text-gray-400">
                        {new Date(audit.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => navigate(`/audit/${audit.id}`)}
                      className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
                      title="View Results"
                    >
                      <EyeIcon className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => handleDeleteAudit(audit.id, audit.website_url)}
                      disabled={deletingIds.has(audit.id)}
                      className="p-2 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Delete Audit"
                    >
                      {deletingIds.has(audit.id) ? (
                        <div className="animate-spin h-5 w-5 border-2 border-red-600 border-t-transparent rounded-full"></div>
                      ) : (
                        <TrashIcon className="h-5 w-5" />
                      )}
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default AuditList;