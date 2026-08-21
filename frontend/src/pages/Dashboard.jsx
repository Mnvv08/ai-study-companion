import React, { useContext, useState, useEffect } from 'react';
import { AuthContext } from '../context/AuthContext';
import apiClient from '../api/client';

const Dashboard = () => {
  const { user, logout } = useContext(AuthContext);

  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [loadingList, setLoadingList] = useState(false);
  
  // Upload state
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');

  // 1. Fetch documents list on mount
  const fetchDocuments = async () => {
    setLoadingList(true);
    try {
      const response = await apiClient.get('/documents');
      setDocuments(response.data);
    } catch (err) {
      console.error('Failed to fetch documents', err);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  // 2. Poll status for pending documents
  const pendingIds = documents
    .filter((doc) => doc.status === 'pending')
    .map((doc) => doc.id);

  useEffect(() => {
    if (pendingIds.length === 0) return;

    const intervals = pendingIds.map((id) => {
      return setInterval(async () => {
        try {
          const response = await apiClient.get(`/documents/${id}/status`);
          const updatedDoc = response.data;
          
          if (updatedDoc.status !== 'pending') {
            // Update document status in the state
            setDocuments((prevDocs) =>
              prevDocs.map((doc) =>
                doc.id === id ? { ...doc, status: updatedDoc.status } : doc
              )
            );
          }
        } catch (err) {
          console.error(`Failed to poll status for document ${id}`, err);
        }
      }, 3000);
    });

    return () => {
      intervals.forEach((intervalId) => clearInterval(intervalId));
    };
  }, [pendingIds.join(',')]);

  // 3. Handle File selection and upload
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setUploadError('');
      setUploadSuccess('');
    }
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setUploadError('Please select a file to upload first.');
      return;
    }

    setUploading(true);
    setUploadError('');
    setUploadSuccess('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await apiClient.post('/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setUploadSuccess(`Successfully uploaded '${file.name}'!`);
      setFile(null);
      // Reset the file input element manually
      e.target.reset();

      // Refresh documents list to show the new entry immediately
      const refreshResponse = await apiClient.get('/documents');
      setDocuments(refreshResponse.data);
    } catch (err) {
      console.error(err);
      setUploadError(
        err.response?.data?.detail || 'Failed to upload document. Please try again.'
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 justify-between items-center">
            <div className="flex-shrink-0 flex items-center space-x-2">
              <span className="text-xl font-bold text-indigo-650 bg-gradient-to-r from-indigo-600 to-indigo-800 bg-clip-text text-transparent">
                AI Study Companion
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700">
                Welcome, <strong>{user?.name || 'Student'}</strong>!
              </span>
              <button
                onClick={logout}
                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Container */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
        
        {/* SECTION 1: Document Upload */}
        <section className="bg-white rounded-2xl p-6 shadow-md border border-gray-100">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Upload Study Material</h2>
          
          {uploadSuccess && (
            <div className="mb-4 rounded-md bg-green-50 p-4 text-sm text-green-700 border border-green-200">
              {uploadSuccess}
            </div>
          )}

          {uploadError && (
            <div className="mb-4 rounded-md bg-red-50 p-4 text-sm text-red-700 border border-red-200">
              {uploadError}
            </div>
          )}

          <form onSubmit={handleUploadSubmit} className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <div className="flex-grow">
                <input
                  type="file"
                  accept=".pdf,.pptx,.ppt"
                  onChange={handleFileChange}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"
                />
              </div>
              <button
                type="submit"
                disabled={uploading || !file}
                className="inline-flex justify-center items-center rounded-md bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm"
              >
                {uploading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Uploading...
                  </>
                ) : (
                  'Upload File'
                )}
              </button>
            </div>
            <p className="text-xs text-gray-500">
              Supported file formats: PDF, PPTX, PPT (Max 20MB)
            </p>
          </form>
        </section>

        {/* SECTION 2: Document List */}
        <section className="bg-white rounded-2xl p-6 shadow-md border border-gray-100">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold text-gray-900">Your Documents</h2>
            <button
              onClick={fetchDocuments}
              className="text-sm font-medium text-indigo-650 hover:text-indigo-800 transition"
            >
              Refresh List
            </button>
          </div>

          {loadingList && documents.length === 0 ? (
            <div className="text-center py-8 text-sm text-gray-500">Loading documents...</div>
          ) : documents.length === 0 ? (
            <div className="text-center py-12 text-sm text-gray-500 border-2 border-dashed border-gray-200 rounded-xl">
              No documents uploaded yet. Upload your first lecture note or slides above!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Filename
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Uploaded At
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {documents.map((doc) => {
                    const isSelected = selectedDocId === doc.id;
                    const isProcessed = doc.status === 'processed';

                    return (
                      <tr
                        key={doc.id}
                        onClick={() => isProcessed && setSelectedDocId(doc.id)}
                        className={`transition cursor-pointer ${
                          isSelected
                            ? 'bg-indigo-50 hover:bg-indigo-100'
                            : isProcessed
                            ? 'hover:bg-gray-50'
                            : 'opacity-60 cursor-not-allowed'
                        }`}
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          <div className="flex items-center space-x-2">
                            {isSelected && <span className="text-indigo-600">✓</span>}
                            <span>{doc.filename}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 uppercase">
                          {doc.file_type}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <span
                            className={`inline-flex px-2 py-1 text-xs font-semibold leading-5 rounded-full ${
                              doc.status === 'processed'
                                ? 'bg-green-100 text-green-800'
                                : doc.status === 'failed'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-yellow-100 text-yellow-800 animate-pulse'
                            }`}
                          >
                            {doc.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(doc.created_at).toLocaleString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          
          {selectedDocId && (
            <div className="mt-4 text-sm text-gray-700 bg-indigo-50/50 p-3 rounded-lg border border-indigo-100 flex justify-between items-center">
              <span>
                Selected Document ID: <strong className="font-mono text-indigo-700">{selectedDocId}</strong>
              </span>
              <button
                onClick={() => setSelectedDocId(null)}
                className="text-xs text-red-650 hover:text-red-850 font-semibold"
              >
                Clear Selection
              </button>
            </div>
          )}
        </section>

      </main>
    </div>
  );
};

export default Dashboard;
