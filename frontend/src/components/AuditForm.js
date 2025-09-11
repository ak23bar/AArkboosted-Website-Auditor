import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { auditsAPI } from '../api';

const AuditForm = () => {
  const [loading, setLoading] = useState(false);
  const [website_url, setWebsiteUrl] = useState('');
  const [website_type, setWebsiteType] = useState('website');
  const navigate = useNavigate();

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!website_url || !website_type) return;
    
    setLoading(true);
    try {
      const response = await auditsAPI.create({ website_url, website_type });
      toast.success('Audit started! Results will be available shortly.');
      navigate('/');
    } catch (error) {
      toast.error('Failed to start audit. Please try again.');
    } finally {
      setLoading(false);
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
                New Website Audit
              </h1>
            </div>
            <button
              onClick={() => navigate('/')}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <ArrowLeftIcon className="h-4 w-4 mr-2" />
              Back to Dashboard
            </button>
          </div>
        </div>
      </header>
      
      <div className="py-8">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/')}
            className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-4"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            Back to Audits
          </button>
          <h1 className="text-2xl font-bold text-gray-900">New Website Audit</h1>
          <p className="mt-2 text-sm text-gray-700">
            Enter a website URL to start a comprehensive audit
          </p>
        </div>

        {/* Form */}
        <div className="bg-white shadow sm:rounded-lg">
          <form onSubmit={onSubmit} className="space-y-6 p-6">
            {/* Website URL */}
            <div>
              <label htmlFor="website_url" className="block text-sm font-medium text-gray-700">
                Website URL *
              </label>
              <input
                type="url"
                value={website_url}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="https://example.com"
                disabled={loading}
                required
              />
              <p className="mt-1 text-sm text-gray-500">
                Include http:// or https://. We'll analyze the live website.
              </p>
            </div>

            {/* Website Type */}
            <div>
              <label htmlFor="website_type" className="block text-sm font-medium text-gray-700">
                Website Type *
              </label>
              <select
                value={website_type}
                onChange={(e) => setWebsiteType(e.target.value)}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                disabled={loading}
                required
              >
                <option value="landing-page">Landing Page (Single Page)</option>
                <option value="website">Business Website (3-5 Pages)</option>
                <option value="large-website">Large Website (10+ Pages)</option>
                <option value="e-commerce">E-commerce Store</option>
                <option value="blog">Blog/News Site</option>
                <option value="portfolio">Portfolio/Personal Site</option>
                <option value="search-engine">Search Engine</option>
                <option value="web-app">Web Application</option>
                <option value="corporate">Corporate/Enterprise Site</option>
              </select>
              <p className="mt-1 text-sm text-gray-500">
                Choose the type that best describes the website. This affects which criteria are used for scoring.
              </p>
            </div>

            {/* Submit Button */}
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading || !website_url || !website_type}
                className="ml-3 inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="flex items-center">
                    <div className="animate-spin -ml-1 mr-3 h-5 w-5 border-2 border-white border-t-transparent rounded-full"></div>
                    Starting Audit...
                  </div>
                ) : (
                  'Start Audit'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
    </div>
  );
};

export default AuditForm;