import React, { useContext, useState, useEffect, useRef } from 'react';
import { AuthContext } from '../context/AuthContext';
import apiClient from '../api/client';

const Dashboard = () => {
  const { user, logout } = useContext(AuthContext);

  // Documents listing & selection
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [loadingList, setLoadingList] = useState(false);
  
  // Upload state
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');

  // Right Panel tab selection: 'chat' | 'notes'
  const [activeTab, setActiveTab] = useState('chat');

  // Q&A Chat states
  const [chatHistory, setChatHistory] = useState([]);
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const chatEndRef = useRef(null);

  // Study Notes states
  const [sessionNotes, setSessionNotes] = useState({}); // docId -> notesData
  const [notesLoading, setNotesLoading] = useState(false);
  const [notesError, setNotesError] = useState('');
  const [expandedSections, setExpandedSections] = useState({}); // sectionIndex -> bool

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

  // 3. Clear Chat history when selection changes
  useEffect(() => {
    setChatHistory([]);
    setQuestion('');
    setNotesError('');
    setActiveTab('chat'); // default to chat on document change
  }, [selectedDocId]);

  // Scroll to bottom of chat history on updates
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, asking]);

  // 4. Handle File selection and upload
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
      await apiClient.post('/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setUploadSuccess(`Successfully uploaded '${file.name}'!`);
      setFile(null);
      e.target.reset();

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

  // 5. Handle Chat Question submission
  const handleAskSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim() || !selectedDocId) return;

    const currentQuestion = question.trim();
    setQuestion('');
    setAsking(true);

    const messageIndex = chatHistory.length;
    setChatHistory((prev) => [
      ...prev,
      { question: currentQuestion, answer: null, error: null, loading: true },
    ]);

    try {
      const response = await apiClient.post('/qa/ask', {
        document_id: selectedDocId,
        question: currentQuestion,
      });

      setChatHistory((prev) =>
        prev.map((msg, idx) =>
          idx === messageIndex ? { ...msg, answer: response.data.answer, loading: false } : msg
        )
      );
    } catch (err) {
      console.error(err);
      const errMsg =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        'Failed to get response. Please check your connection or try again.';

      setChatHistory((prev) =>
        prev.map((msg, idx) =>
          idx === messageIndex ? { ...msg, error: errMsg, loading: false } : msg
        )
      );
    } finally {
      setAsking(false);
    }
  };

  // 6. Handle Notes Generation & Caching
  const triggerNotesGeneration = async (force = false) => {
    if (!selectedDocId) return;
    setNotesLoading(true);
    setNotesError('');

    try {
      const response = await apiClient.post('/notes/generate', {
        document_id: selectedDocId,
        force_regenerate: force,
      });

      const notesData = response.data;
      
      // Cache in session mapping
      setSessionNotes((prev) => ({
        ...prev,
        [selectedDocId]: notesData,
      }));

      // Initialize sections expand states (First expanded, others collapsed)
      const initialExpand = {};
      if (notesData.sections) {
        notesData.sections.forEach((_, idx) => {
          initialExpand[idx] = idx === 0;
        });
      }
      setExpandedSections(initialExpand);
    } catch (err) {
      console.error(err);
      setNotesError(
        err.response?.data?.detail || 'Failed to generate study notes. Please retry.'
      );
    } finally {
      setNotesLoading(false);
    }
  };

  // Check if notes already exist in session
  const currentNotes = sessionNotes[selectedDocId];

  const toggleSection = (index) => {
    setExpandedSections((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const selectedDocName = documents.find((d) => d.id === selectedDocId)?.filename;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Navbar */}
      <nav className="bg-white shadow-sm flex-shrink-0">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 justify-between items-center">
            <div className="flex-shrink-0 flex items-center space-x-2">
              <span className="text-xl font-bold text-indigo-600 bg-gradient-to-r from-indigo-600 to-indigo-800 bg-clip-text text-transparent">
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

      {/* Two-Column Grid Layout */}
      <div className="flex-grow mx-auto max-w-7xl w-full px-4 py-8 sm:px-6 lg:px-8 grid grid-cols-1 lg:grid-cols-12 gap-8 overflow-hidden">
        
        {/* Left Column (Upload + List) - 5 Cols */}
        <div className="lg:col-span-5 space-y-6 flex flex-col overflow-y-auto pr-1">
          {/* SECTION 1: Document Upload */}
          <section className="bg-white rounded-2xl p-6 shadow-md border border-gray-100 flex-shrink-0">
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
              <div className="flex flex-col gap-3">
                <input
                  type="file"
                  accept=".pdf,.pptx,.ppt"
                  onChange={handleFileChange}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"
                />
                <button
                  type="submit"
                  disabled={uploading || !file}
                  className="inline-flex justify-center items-center w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm"
                >
                  {uploading ? 'Uploading...' : 'Upload File'}
                </button>
              </div>
              <p className="text-xs text-gray-500 text-center">
                Supported: PDF, PPTX, PPT (Max 20MB)
              </p>
            </form>
          </section>

          {/* SECTION 2: Document List */}
          <section className="bg-white rounded-2xl p-6 shadow-md border border-gray-100 flex-grow flex flex-col overflow-hidden">
            <div className="flex justify-between items-center mb-4 flex-shrink-0">
              <h2 className="text-lg font-bold text-gray-900">Your Documents</h2>
              <button
                onClick={fetchDocuments}
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-850"
              >
                Refresh List
              </button>
            </div>

            <div className="flex-grow overflow-y-auto">
              {loadingList && documents.length === 0 ? (
                <div className="text-center py-8 text-sm text-gray-500">Loading documents...</div>
              ) : documents.length === 0 ? (
                <div className="text-center py-12 text-sm text-gray-400 border-2 border-dashed border-gray-200 rounded-xl">
                  No documents uploaded yet.
                </div>
              ) : (
                <ul className="space-y-3">
                  {documents.map((doc) => {
                    const isSelected = selectedDocId === doc.id;
                    const isProcessed = doc.status === 'processed';

                    return (
                      <li
                        key={doc.id}
                        onClick={() => isProcessed && setSelectedDocId(doc.id)}
                        className={`p-4 rounded-xl border text-left transition ${
                          isProcessed ? 'cursor-pointer' : 'opacity-65 cursor-not-allowed'
                        } ${
                          isSelected
                            ? 'bg-indigo-50 border-indigo-300 ring-2 ring-indigo-500/20'
                            : 'bg-white border-gray-200 hover:bg-gray-50'
                        }`}
                      >
                        <div className="flex justify-between items-start gap-2">
                          <div className="font-semibold text-sm text-gray-900 truncate">
                            {doc.filename}
                          </div>
                          <span
                            className={`inline-flex px-2 py-0.5 text-2xs font-semibold rounded-full uppercase ${
                              doc.status === 'processed'
                                ? 'bg-green-50 text-green-700 border border-green-200'
                                : doc.status === 'failed'
                                ? 'bg-red-50 text-red-700 border border-red-200'
                                : 'bg-yellow-50 text-yellow-700 border border-yellow-200 animate-pulse'
                            }`}
                          >
                            {doc.status}
                          </span>
                        </div>
                        <div className="flex justify-between items-center mt-2 text-2xs text-gray-500">
                          <span>Format: {doc.file_type}</span>
                          <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </section>
        </div>

        {/* Right Column (Q&A / Notes Tabs Panel) - 7 Cols */}
        <div className="lg:col-span-7 bg-white rounded-2xl shadow-md border border-gray-100 overflow-hidden flex flex-col min-h-[450px]">
          
          {/* Header & Tabs */}
          <div className="bg-gray-50 border-b border-gray-100 p-4 flex-shrink-0 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`text-sm font-bold pb-1 border-b-2 px-1 transition ${
                    activeTab === 'chat'
                      ? 'border-indigo-600 text-indigo-700'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Q&amp;A Chat
                </button>
                <button
                  onClick={() => setActiveTab('notes')}
                  className={`text-sm font-bold pb-1 border-b-2 px-1 transition ${
                    activeTab === 'notes'
                      ? 'border-indigo-600 text-indigo-700'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Study Notes
                </button>
              </div>
              {selectedDocId && (
                <p className="text-2xs text-gray-500 mt-1 truncate max-w-sm">
                  Active file: {selectedDocName}
                </p>
              )}
            </div>
            {selectedDocId && (
              <button
                onClick={() => setSelectedDocId(null)}
                className="text-2xs font-bold text-red-600 hover:text-red-800 self-start sm:self-auto"
              >
                Clear Selection
              </button>
            )}
          </div>

          {/* Panel Contents */}
          {!selectedDocId ? (
            <div className="flex-grow flex flex-col items-center justify-center p-8 text-center bg-gray-50/50">
              <div className="w-16 h-16 rounded-full bg-indigo-50 flex items-center justify-center text-3xl mb-4 shadow-inner">
                📚
              </div>
              <h3 className="text-base font-bold text-gray-900">No Document Selected</h3>
              <p className="text-sm text-gray-500 mt-2 max-w-sm leading-relaxed">
                Select a processed document on the left to start asking questions or generate structured study notes.
              </p>
            </div>
          ) : activeTab === 'chat' ? (
            /* TAB 1: Chat interface */
            <div className="flex-grow flex flex-col justify-between overflow-hidden">
              <div className="flex-grow p-4 overflow-y-auto space-y-4">
                {chatHistory.length === 0 && !asking && (
                  <div className="text-center py-12 text-slate-400 text-xs italic">
                    Type a question below to query the selected study material...
                  </div>
                )}

                {chatHistory.map((chat, idx) => {
                  const isRefusal = chat.answer === "I couldn't find this in your uploaded material.";
                  
                  return (
                    <div key={idx} className="space-y-2">
                      <div className="flex justify-end">
                        <div className="bg-indigo-650 bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-md text-sm font-medium shadow-sm">
                          {chat.question}
                        </div>
                      </div>

                      <div className="flex justify-start">
                        {chat.loading ? (
                          <div className="bg-gray-100 text-gray-500 rounded-2xl rounded-tl-sm px-4 py-2.5 flex items-center space-x-2 text-sm shadow-sm">
                            <span className="flex h-2 w-2 relative">
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                              <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                            </span>
                            <span>Thinking...</span>
                          </div>
                        ) : chat.error ? (
                          <div className="bg-red-50 text-red-700 border border-red-150 rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-md text-sm shadow-sm">
                            <strong className="block text-2xs uppercase tracking-wider text-red-650 font-bold mb-1">
                              System Error
                            </strong>
                            {chat.error}
                          </div>
                        ) : (
                          <div
                            className={`rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-md text-sm leading-relaxed shadow-sm ${
                              isRefusal
                                ? 'bg-gray-50 text-gray-500 italic border border-gray-200'
                                : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {chat.answer}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
                <div ref={chatEndRef} />
              </div>

              <form onSubmit={handleAskSubmit} className="p-4 bg-gray-50 border-t border-gray-100 flex-shrink-0 flex gap-2">
                <input
                  type="text"
                  required
                  placeholder="Ask a question about the document..."
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  disabled={asking}
                  className="flex-grow rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-60 bg-white"
                />
                <button
                  type="submit"
                  disabled={asking || !question.trim()}
                  className="rounded-lg bg-indigo-600 text-white px-5 py-2.5 text-sm font-semibold hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 transition shadow-sm"
                >
                  Ask
                </button>
              </form>
            </div>
          ) : (
            /* TAB 2: Notes Interface */
            <div className="flex-grow flex flex-col overflow-hidden bg-gray-50/30">
              
              {!currentNotes && !notesLoading && (
                <div className="flex-grow flex flex-col items-center justify-center p-8 text-center">
                  <h3 className="text-base font-bold text-gray-900">Notes Not Generated</h3>
                  <p className="text-xs text-gray-500 mt-2 max-w-xs leading-relaxed">
                    Convert this document's text into structured study notes, key terms, and summary headings.
                  </p>
                  
                  {notesError && (
                    <div className="mt-4 max-w-sm rounded-md bg-red-50 p-3 text-xs text-red-700 border border-red-200">
                      {notesError}
                    </div>
                  )}

                  <button
                    onClick={() => triggerNotesGeneration(false)}
                    className="mt-5 rounded-lg bg-indigo-600 text-white px-5 py-2.5 text-xs font-bold hover:bg-indigo-700 shadow-md transition"
                  >
                    Generate Notes
                  </button>
                </div>
              )}

              {notesLoading && (
                <div className="flex-grow flex flex-col items-center justify-center p-8 text-center">
                  <svg className="animate-spin h-10 w-10 text-indigo-600 mb-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <h4 className="text-sm font-bold text-gray-900">Structuring Study Notes...</h4>
                  <p className="text-2xs text-gray-500 mt-1">This takes 5-10 seconds to read and organize the source content.</p>
                </div>
              )}

              {currentNotes && !notesLoading && (
                <div className="flex-grow flex flex-col overflow-hidden">
                  
                  {/* Notes Control Subheader */}
                  <div className="bg-white border-b border-gray-150 px-4 py-2 flex justify-between items-center flex-shrink-0 text-xs">
                    <span className="font-semibold text-gray-800">
                      Title: {currentNotes.title || 'Structured Study Notes'}
                    </span>
                    <button
                      onClick={() => triggerNotesGeneration(true)}
                      className="text-2xs text-indigo-600 hover:text-indigo-850 font-bold hover:underline"
                    >
                      Regenerate
                    </button>
                  </div>

                  {notesError && (
                    <div className="bg-red-50 text-red-700 text-2xs p-3 border-b border-red-200">
                      ⚠️ {notesError} (Showing last cached notes)
                    </div>
                  )}

                  {/* Dual Panel Notes view */}
                  <div className="flex-grow flex flex-col md:flex-row overflow-hidden">
                    
                    {/* Left Panel: Sections List (Collapsible) */}
                    <div className="flex-grow md:w-3/5 p-4 overflow-y-auto space-y-3">
                      {currentNotes.sections?.map((section, idx) => {
                        const isExpanded = !!expandedSections[idx];
                        
                        return (
                          <div key={idx} className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-2xs">
                            <button
                              onClick={() => toggleSection(idx)}
                              className="w-full text-left px-4 py-3 bg-gray-50 hover:bg-gray-100 flex justify-between items-center transition border-b border-gray-100"
                            >
                              <span className="font-bold text-sm text-gray-900">{section.heading}</span>
                              <span className="text-xs text-gray-400 font-semibold">{isExpanded ? 'Collapse ▲' : 'Expand ▼'}</span>
                            </button>

                            {isExpanded && (
                              <ul className="p-4 space-y-2 list-disc list-inside text-xs text-gray-700 leading-relaxed bg-white">
                                {section.points?.map((pt, pIdx) => (
                                  <li key={pIdx} className="pl-1">
                                    {pt}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Right Panel: Key Terms Sidebar */}
                    <div className="md:w-2/5 bg-gray-50 border-t md:border-t-0 md:border-l border-gray-200 p-4 overflow-y-auto flex flex-col">
                      <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Key Terms</h3>
                      
                      {currentNotes.key_terms?.length === 0 ? (
                        <div className="text-center py-6 text-2xs text-gray-400 italic bg-white rounded-xl border border-gray-100">
                          No key definitions listed.
                        </div>
                      ) : (
                        <ul className="space-y-3">
                          {currentNotes.key_terms?.map((term, tIdx) => (
                            <li key={tIdx} className="bg-white p-3 rounded-xl border border-gray-250/60 border-gray-200 shadow-2xs">
                              <div className="font-bold text-xs text-indigo-750 text-indigo-700">{term.term}</div>
                              <div className="text-2xs text-gray-600 mt-1 leading-normal">{term.definition}</div>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                  </div>

                </div>
              )}

            </div>
          )}

        </div>

      </div>
    </div>
  );
};

export default Dashboard;
