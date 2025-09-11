import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { TrashIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { auditsAPI } from '../api';
import AuditList from './AuditList';

const Dashboard = () => {
  const navigate = useNavigate();
  const [isClearing, setIsClearing] = useState(false);

  const handleClearAllAudits = async () => {
    if (!window.confirm('Are you sure you want to clear all audits? This action cannot be undone.')) {
      return;
    }
    
    setIsClearing(true);
    try {
      await auditsAPI.clearAll();
      toast.success('All audits cleared successfully');
      // Refresh the page to update the audit list
      window.location.reload();
    } catch (error) {
      console.error('Failed to clear audits:', error);
      toast.error('Failed to clear audits. Please try again.');
    } finally {
      setIsClearing(false);
    }
  };

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
                Website Audit Tool
              </h1>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={handleClearAllAudits}
                disabled={isClearing}
                className="inline-flex items-center px-3 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <TrashIcon className="h-4 w-4 mr-2" />
                {isClearing ? 'Clearing...' : 'Clear All'}
              </button>
              <button
                onClick={() => navigate('/new-audit')}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                New Audit
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <AuditList />
      </main>
    </div>
  );
};

export default Dashboard;
