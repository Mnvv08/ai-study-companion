import React, { useContext, useState, useEffect, useRef } from 'react';
import { AuthContext } from '../context/AuthContext';
import apiClient from '../api/client';

const Dashboard = () => {
  const { user, logout } = useContext(AuthContext);

  // View state: 'workspace' | 'analytics'
  const [currentView, setCurrentView] = useState('workspace');

  // Documents listing & selection
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [loadingList, setLoadingList] = useState(false);
  
  // Upload state
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');

  // Right Panel tab selection: 'chat' | 'notes' | 'flashcards' | 'mcqs' | 'short_answer'
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

  // Flashcards states
  const [sessionFlashcards, setSessionFlashcards] = useState({}); // docId -> flashcardsList
  const [flashcardsLoading, setFlashcardsLoading] = useState(false);
  const [flashcardsError, setFlashcardsError] = useState('');
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [topicFilter, setTopicFilter] = useState('All');

  // MCQ states
  const [sessionMCQs, setSessionMCQs] = useState({}); // docId -> { quiz_id, questions: [] }
  const [mcqsLoading, setMcqsLoading] = useState(false);
  const [mcqsError, setMcqsError] = useState('');
  const [currentMcqIndex, setCurrentMcqIndex] = useState(0);
  const [mcqAnswers, setMcqAnswers] = useState({}); // questionId -> optionIndex (0-3)
  const [quizResult, setQuizResult] = useState(null);
  const [submittingQuiz, setSubmittingQuiz] = useState(false);

  // Short Answer states
  const [sessionShortAnswers, setSessionShortAnswers] = useState({}); // docId -> { quiz_id, questions: [] }
  const [saLoading, setSaLoading] = useState(false);
  const [saError, setSaError] = useState('');
  const [currentSaIndex, setCurrentSaIndex] = useState(0);
  const [saAnswers, setSaAnswers] = useState({}); // questionId -> studentText
  const [saQuizResult, setSaQuizResult] = useState(null);
  const [submittingSaQuiz, setSubmittingSaQuiz] = useState(false);

  // Quiz Performance History states
  const [historyList, setHistoryList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Analytics states
  const [weakTopics, setWeakTopics] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [analyticsError, setAnalyticsError] = useState('');

  // 1. Fetch documents list and history on mount
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

  const fetchQuizHistory = async () => {
    setLoadingHistory(true);
    try {
      const response = await apiClient.get('/quizzes/history');
      setHistoryList(response.data);
    } catch (err) {
      console.error('Failed to fetch quiz history', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const fetchAnalytics = async () => {
    setLoadingAnalytics(true);
    setAnalyticsError('');
    try {
      const [topicsRes, recsRes] = await Promise.all([
        apiClient.get('/analytics/weak-topics'),
        apiClient.get('/analytics/recommendations'),
      ]);
      setWeakTopics(topicsRes.data.weak_topics || []);
      setRecommendations(recsRes.data.recommendations || []);
    } catch (err) {
      console.error('Failed to fetch analytics', err);
      setAnalyticsError(
        err.response?.data?.detail || 'Failed to load progress analytics. Please try again.'
      );
    } finally {
      setLoadingAnalytics(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
    fetchQuizHistory();
  }, []);

  // Fetch analytics when view changes to My Progress
  useEffect(() => {
    if (currentView === 'analytics') {
      fetchAnalytics();
    }
  }, [currentView]);

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

  // 3. Clear Right Panel states when selection changes
  useEffect(() => {
    setChatHistory([]);
    setQuestion('');
    setNotesError('');
    setFlashcardsError('');
    setMcqsError('');
    setSaError('');
    setCurrentCardIndex(0);
    setCurrentMcqIndex(0);
    setCurrentSaIndex(0);
    setFlipped(false);
    setTopicFilter('All');
    setMcqAnswers({});
    setSaAnswers({});
    setQuizResult(null);
    setSaQuizResult(null);
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
      
      setSessionNotes((prev) => ({
        ...prev,
        [selectedDocId]: notesData,
      }));

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

  // 7. Handle Flashcards Generation & Caching
  const triggerFlashcardsGeneration = async (force = false) => {
    if (!selectedDocId) return;
    setFlashcardsLoading(true);
    setFlashcardsError('');
    setCurrentCardIndex(0);
    setFlipped(false);
    setTopicFilter('All');

    try {
      const response = await apiClient.post('/flashcards/generate', {
        document_id: selectedDocId,
        force_regenerate: force,
      });

      const cardsList = response.data.flashcards;

      setSessionFlashcards((prev) => ({
        ...prev,
        [selectedDocId]: cardsList,
      }));
    } catch (err) {
      console.error(err);
      setFlashcardsError(
        err.response?.data?.detail || 'Failed to generate flashcards. Please try again.'
      );
    } finally {
      setFlashcardsLoading(false);
    }
  };

  // 8. Handle MCQ Generation & Quiz Submission
  const triggerMCQGeneration = async (force = false) => {
    if (!selectedDocId) return;
    setMcqsLoading(true);
    setMcqsError('');
    setCurrentMcqIndex(0);
    setMcqAnswers({});
    setQuizResult(null);

    try {
      const response = await apiClient.post('/mcqs/generate', {
        document_id: selectedDocId,
        force_regenerate: force,
      });

      setSessionMCQs((prev) => ({
        ...prev,
        [selectedDocId]: {
          quiz_id: response.data.quiz_id,
          questions: response.data.questions,
        },
      }));
    } catch (err) {
      console.error(err);
      setMcqsError(
        err.response?.data?.detail || 'Failed to generate MCQ practice quiz. Please retry.'
      );
    } finally {
      setMcqsLoading(false);
    }
  };

  const handleQuizSubmit = async () => {
    const activeQuiz = sessionMCQs[selectedDocId];
    if (!selectedDocId || !activeQuiz) return;

    setSubmittingQuiz(true);
    setMcqsError('');

    const formattedAnswers = activeQuiz.questions.map((q) => {
      const selection = mcqAnswers[q.id];
      return {
        question_id: q.id,
        student_answer: selection !== undefined ? String(selection) : '',
      };
    });

    try {
      const response = await apiClient.post(`/quizzes/${activeQuiz.quiz_id}/submit`, {
        answers: formattedAnswers,
      });
      setQuizResult(response.data);
      // Refresh history list and analytics immediately
      fetchQuizHistory();
      fetchAnalytics();
    } catch (err) {
      console.error(err);
      setMcqsError(
        err.response?.data?.detail || 'Failed to submit quiz results. Please try again.'
      );
    } finally {
      setSubmittingQuiz(false);
    }
  };

  // 9. Handle Short-Answer Quiz Generation & Submission
  const triggerSAGeneration = async (force = false) => {
    if (!selectedDocId) return;
    setSaLoading(true);
    setSaError('');
    setCurrentSaIndex(0);
    setSaAnswers({});
    setSaQuizResult(null);

    try {
      const response = await apiClient.post('/short-answer/generate', {
        document_id: selectedDocId,
        force_regenerate: force,
      });

      setSessionShortAnswers((prev) => ({
        ...prev,
        [selectedDocId]: {
          quiz_id: response.data.quiz_id,
          questions: response.data.questions,
        },
      }));
    } catch (err) {
      console.error(err);
      setSaError(
        err.response?.data?.detail || 'Failed to generate Short-Answer practice quiz. Please retry.'
      );
    } finally {
      setSaLoading(false);
    }
  };

  const handleSaQuizSubmit = async () => {
    const activeSaQuiz = sessionShortAnswers[selectedDocId];
    if (!selectedDocId || !activeSaQuiz) return;

    setSubmittingSaQuiz(true);
    setSaError('');

    const formattedAnswers = activeSaQuiz.questions.map((q) => {
      const textVal = saAnswers[q.id] || '';
      return {
        question_id: q.id,
        student_answer: textVal.trim(),
      };
    });

    try {
      const response = await apiClient.post(`/quizzes/${activeSaQuiz.quiz_id}/submit`, {
        answers: formattedAnswers,
      });
      setSaQuizResult(response.data);
      // Refresh history list and analytics immediately
      fetchQuizHistory();
      fetchAnalytics();
    } catch (err) {
      console.error(err);
      setSaError(
        err.response?.data?.detail || 'Failed to submit quiz results. Please try again.'
      );
    } finally {
      setSubmittingSaQuiz(false);
    }
  };

  const handleRecommendationClick = (docId) => {
    if (docId && docId !== 'unknown') {
      setSelectedDocId(docId);
      setCurrentView('workspace');
      setActiveTab('notes'); // Open study notes instantly for revision
    }
  };

  // Caching getters
  const currentNotes = sessionNotes[selectedDocId];
  const allFlashcards = sessionFlashcards[selectedDocId] || [];
  const activeQuiz = sessionMCQs[selectedDocId];
  const activeSaQuiz = sessionShortAnswers[selectedDocId];

  // Filter flashcards by topic dropdown
  const uniqueTopics = ['All', ...new Set(allFlashcards.map((c) => c.topic))];
  const filteredFlashcards = topicFilter === 'All'
    ? allFlashcards
    : allFlashcards.filter((c) => c.topic === topicFilter);

  const displayCard = filteredFlashcards[currentCardIndex];

  const handleTopicFilterChange = (e) => {
    setTopicFilter(e.target.value);
    setCurrentCardIndex(0);
    setFlipped(false);
  };

  const nextCard = () => {
    setFlipped(false);
    setCurrentCardIndex((prev) => Math.min(prev + 1, filteredFlashcards.length - 1));
  };

  const prevCard = () => {
    setFlipped(false);
    setCurrentCardIndex((prev) => Math.max(prev - 1, 0));
  };

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
            <div className="flex items-center space-x-6">
              <span className="text-xl font-bold text-indigo-650 bg-gradient-to-r from-indigo-600 to-indigo-800 bg-clip-text text-transparent">
                AI Study Companion
              </span>
              <div className="hidden sm:flex space-x-2">
                <button
                  onClick={() => setCurrentView('workspace')}
                  className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition ${
                    currentView === 'workspace'
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                  }`}
                >
                  Workspace
                </button>
                <button
                  onClick={() => setCurrentView('analytics')}
                  className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition ${
                    currentView === 'analytics'
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                  }`}
                >
                  My Progress
                </button>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {/* Mobile View Toggle Buttons */}
              <div className="flex sm:hidden space-x-1">
                <button
                  onClick={() => setCurrentView('workspace')}
                  className={`px-2.5 py-1 rounded-md text-xs font-bold ${
                    currentView === 'workspace' ? 'bg-indigo-550 bg-indigo-600 text-white' : 'text-gray-500'
                  }`}
                >
                  Study
                </button>
                <button
                  onClick={() => setCurrentView('analytics')}
                  className={`px-2.5 py-1 rounded-md text-xs font-bold ${
                    currentView === 'analytics' ? 'bg-indigo-550 bg-indigo-600 text-white' : 'text-gray-500'
                  }`}
                >
                  Progress
                </button>
              </div>

              <span className="text-sm text-gray-705 text-gray-700 hidden md:inline">
                Welcome, <strong>{user?.name || 'Student'}</strong>!
              </span>
              <button
                onClick={logout}
                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs sm:text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Container */}
      {currentView === 'workspace' ? (
        /* VIEW 1: Study Workspace Grid (Original upload/documents/tabs view) */
        <div className="flex-grow mx-auto max-w-7xl w-full px-4 py-8 sm:px-6 lg:px-8 space-y-8 overflow-y-auto">
          
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Left Column (Upload + List) - 5 Cols */}
            <div className="lg:col-span-5 space-y-6 flex flex-col">
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
              <section className="bg-white rounded-2xl p-6 shadow-md border border-gray-100 flex-grow flex flex-col min-h-[300px]">
                <div className="flex justify-between items-center mb-4 flex-shrink-0">
                  <h2 className="text-lg font-bold text-gray-900">Your Documents</h2>
                  <button
                    onClick={fetchDocuments}
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-850"
                  >
                    Refresh List
                  </button>
                </div>

                <div className="flex-grow overflow-y-auto max-h-[350px]">
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

            {/* Right Column (Q&A / Notes / Flashcards / MCQ / Short Answer Tabs Panel) - 7 Cols */}
            <div className="lg:col-span-7 bg-white rounded-2xl shadow-md border border-gray-100 overflow-hidden flex flex-col min-h-[450px]">
              
              {/* Header & Tabs */}
              <div className="bg-gray-50 border-b border-gray-100 p-4 flex-shrink-0 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
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
                    <button
                      onClick={() => setActiveTab('flashcards')}
                      className={`text-sm font-bold pb-1 border-b-2 px-1 transition ${
                        activeTab === 'flashcards'
                          ? 'border-indigo-600 text-indigo-700'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      Flashcards
                    </button>
                    <button
                      onClick={() => setActiveTab('mcqs')}
                      className={`text-sm font-bold pb-1 border-b-2 px-1 transition ${
                        activeTab === 'mcqs'
                      ? 'border-indigo-600 text-indigo-700'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  MCQ Quiz
                </button>
                <button
                  onClick={() => setActiveTab('short_answer')}
                  className={`text-sm font-bold pb-1 border-b-2 px-1 transition ${
                    activeTab === 'short_answer'
                      ? 'border-indigo-600 text-indigo-700'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Short-Answer
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
                🎓
              </div>
              <h3 className="text-base font-bold text-gray-900">No Document Selected</h3>
              <p className="text-sm text-gray-500 mt-2 max-w-sm leading-relaxed">
                Select a processed document on the left to start asking questions, generate study notes, practice flashcards, or take MCQ/Short-Answer tests.
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
                        <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-md text-sm font-medium shadow-sm">
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
          ) : activeTab === 'notes' ? (
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

                  <div className="flex-grow flex flex-col md:flex-row overflow-hidden">
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

                    <div className="md:w-2/5 bg-gray-50 border-t md:border-t-0 md:border-l border-gray-200 p-4 overflow-y-auto flex flex-col">
                      <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Key Terms</h3>
                      
                      {currentNotes.key_terms?.length === 0 ? (
                        <div className="text-center py-6 text-2xs text-gray-400 italic bg-white rounded-xl border border-gray-100">
                          No key definitions listed.
                        </div>
                      ) : (
                        <ul className="space-y-3">
                          {currentNotes.key_terms?.map((term, tIdx) => (
                            <li key={tIdx} className="bg-white p-3 rounded-xl border border-gray-200 shadow-2xs">
                              <div className="font-bold text-xs text-indigo-700">{term.term}</div>
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
          ) : activeTab === 'flashcards' ? (
            /* TAB 3: Flashcards Interface */
            <div className="flex-grow flex flex-col overflow-hidden bg-gray-50/30">
              {allFlashcards.length === 0 && !flashcardsLoading && (
                <div className="flex-grow flex flex-col items-center justify-center p-8 text-center">
                  <h3 className="text-base font-bold text-gray-900">Flashcards Not Generated</h3>
                  <p className="text-xs text-gray-500 mt-2 max-w-xs leading-relaxed">
                    Generate active-recall flashcards with questions and answers based on this study document.
                  </p>

                  {flashcardsError && (
                    <div className="mt-4 max-w-sm rounded-md bg-red-50 p-3 text-xs text-red-700 border border-red-200">
                      {flashcardsError}
                    </div>
                  )}

                  <button
                    onClick={() => triggerFlashcardsGeneration(false)}
                    className="mt-5 rounded-lg bg-indigo-600 text-white px-5 py-2.5 text-xs font-bold hover:bg-indigo-700 shadow-md transition"
                  >
                    Generate Flashcards
                  </button>
                </div>
              )}

              {flashcardsLoading && (
                <div className="flex-grow flex flex-col items-center justify-center p-8 text-center">
                  <svg className="animate-spin h-10 w-10 text-indigo-600 mb-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <h4 className="text-sm font-bold text-gray-900">Creating Flashcards...</h4>
                  <p className="text-2xs text-gray-500 mt-1">Extracting testable concepts and questions...</p>
                </div>
              )}

              {allFlashcards.length > 0 && !flashcardsLoading && (
                <div className="flex-grow flex flex-col p-6 justify-between overflow-y-auto">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                    <div className="flex items-center space-x-2">
                      <label htmlFor="topic-select" className="text-xs font-semibold text-gray-600">
                        Topic:
                      </label>
                      <select
                        id="topic-select"
                        value={topicFilter}
                        onChange={handleTopicFilterChange}
                        className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs font-medium text-gray-700 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                      >
                        {uniqueTopics.map((topic, index) => (
                          <option key={index} value={topic}>
                            {topic}
                          </option>
                        ))}
                      </select>
                    </div>

                    <button
                      onClick={() => triggerFlashcardsGeneration(true)}
                      className="text-2xs text-indigo-600 hover:text-indigo-850 font-bold hover:underline self-end sm:self-auto"
                    >
                      Regenerate Deck
                    </button>
                  </div>

                  {flashcardsError && (
                    <div className="mb-4 rounded-md bg-red-50 p-3 text-xs text-red-700 border border-red-200">
                      ⚠️ {flashcardsError} (Showing cached deck)
                    </div>
                  )}

                  {filteredFlashcards.length === 0 ? (
                    <div className="flex-grow flex items-center justify-center text-center py-12 text-slate-400 text-xs italic">
                      No flashcards found matching the selected topic filter.
                    </div>
                  ) : (
                    <div className="flex-grow flex flex-col justify-center items-center py-4 space-y-6">
                      <div
                        onClick={() => setFlipped(!flipped)}
                        className={`w-full max-w-md min-h-[180px] flex flex-col justify-between p-6 rounded-2xl border cursor-pointer select-none transition-all shadow-md ${
                          flipped
                            ? 'bg-indigo-50 border-indigo-300 ring-4 ring-indigo-500/10'
                            : 'bg-white border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex justify-between items-center text-3xs font-bold uppercase tracking-wider text-gray-400">
                          <span>Topic: {displayCard.topic}</span>
                          <span className={flipped ? 'text-indigo-600' : 'text-gray-400'}>
                            {flipped ? 'Answer' : 'Question'}
                          </span>
                        </div>

                        <div className="my-auto py-4 text-center">
                          {flipped ? (
                            <div className="text-gray-800 text-sm md:text-base font-semibold leading-relaxed">
                              {displayCard.back}
                            </div>
                          ) : (
                            <div className="text-gray-900 text-sm md:text-base font-bold leading-relaxed">
                              {displayCard.front}
                            </div>
                          )}
                        </div>

                        <div className="text-center text-3xs text-slate-400 uppercase tracking-widest">
                          {flipped ? 'Click to show question' : 'Click to flip and show answer'}
                        </div>
                      </div>

                      <div className="text-xs font-semibold text-gray-500">
                        Card {currentCardIndex + 1} of {filteredFlashcards.length}
                      </div>

                      <div className="flex items-center space-x-4">
                        <button
                          onClick={prevCard}
                          disabled={currentCardIndex === 0}
                          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-xs font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-2xs transition"
                        >
                          ◀ Prev
                        </button>
                        <button
                          onClick={nextCard}
                          disabled={currentCardIndex === filteredFlashcards.length - 1}
                          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-xs font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-2xs transition"
                        >
                          Next ▶
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : activeTab === 'mcqs' ? (
            /* TAB 4: MCQ Quiz Interface */
            <div className="flex-grow flex flex-col overflow-hidden bg-gray-50/30">
              
              {!activeQuiz && !mcqsLoading && (
                <div className="flex-grow flex flex-col items-center justify-center p-8 text-center">
                  <h3 className="text-base font-bold text-gray-900">Practice Quiz Not Generated</h3>
                  <p className="text-xs text-gray-500 mt-2 max-w-xs leading-relaxed">
                    Test your understanding with a dynamically generated multiple-choice question quiz.
                  </p>

                  {mcqsError && (
                    <div className="mt-4 max-w-sm rounded-md bg-red-50 p-3 text-xs text-red-700 border border-red-200">
                      {mcqsError}
                    </div>
                  )}

                  <button
                    onClick={() => triggerMCQGeneration(false)}
                    className="mt-5 rounded-lg bg-indigo-600 text-white px-5 py-2.5 text-xs font-bold hover:bg-indigo-700 shadow-md transition"
                  >
                    Generate MCQ Quiz
                  </button>
                </div>
              )}

              {mcqsLoading && (
                <div className="flex-grow flex flex-col items-center justify-center p-8 text-center">
                  <svg className="animate-spin h-10 w-10 text-indigo-600 mb-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <h4 className="text-sm font-bold text-gray-950 text-gray-905">Formulating Practice Quiz...</h4>
                  <p className="text-2xs text-gray-500 mt-1">Creating custom single-answer multiple-choice questions...</p>
                </div>
              )}

              {activeQuiz && !mcqsLoading && (
                <div className="flex-grow flex flex-col p-6 justify-between overflow-y-auto">
                  <div className="bg-white border rounded-xl p-3 flex justify-between items-center flex-shrink-0 text-xs shadow-2xs mb-4">
                    <span className="font-semibold text-gray-800">
                      Quiz Mode: Practice MCQ Test
                    </span>
                    <button
                      onClick={() => triggerMCQGeneration(true)}
                      className="text-2xs text-indigo-600 hover:text-indigo-850 font-bold hover:underline"
                    >
                      Regenerate Quiz
                    </button>
                  </div>

                  {mcqsError && (
                    <div className="mb-4 rounded-md bg-red-50 p-3 text-xs text-red-700 border border-red-200">
                      ⚠️ {mcqsError}
                    </div>
                  )}

                  {!quizResult ? (
                    <div className="flex-grow flex flex-col justify-between">
                      {activeQuiz.questions.length === 0 ? (
                        <div className="text-center py-12 text-gray-500 text-xs italic">
                          No questions generated for this document.
                        </div>
                      ) : (
                        <div className="space-y-6">
                          {(() => {
                            const q = activeQuiz.questions[currentMcqIndex];
                            const selectedOptionIdx = mcqAnswers[q.id];

                            return (
                              <div className="space-y-4">
                                <div className="flex justify-between items-center text-3xs font-bold uppercase tracking-wider text-gray-400">
                                  <span>Concept: {q.topic}</span>
                                  <span>Question {currentMcqIndex + 1} of {activeQuiz.questions.length}</span>
                                </div>
                                <h3 className="text-sm md:text-base font-bold text-gray-900 leading-normal">
                                  {q.question}
                                </h3>

                                <div className="space-y-2.5 pt-2">
                                  {q.options.map((opt, oIdx) => {
                                    const isChosen = selectedOptionIdx === oIdx;
                                    return (
                                      <button
                                        key={oIdx}
                                        onClick={() =>
                                          setMcqAnswers((prev) => ({ ...prev, [q.id]: oIdx }))
                                        }
                                        className={`w-full text-left px-4 py-3 rounded-xl border text-xs md:text-sm font-semibold transition ${
                                          isChosen
                                            ? 'bg-indigo-50 border-indigo-400 text-indigo-900 ring-2 ring-indigo-500/10'
                                            : 'bg-white border-gray-200 hover:bg-gray-50 text-gray-700'
                                        }`}
                                      >
                                        <div className="flex items-center space-x-3">
                                          <div
                                            className={`h-4 w-4 rounded-full border flex items-center justify-center flex-shrink-0 ${
                                              isChosen ? 'border-indigo-600 bg-indigo-600' : 'border-gray-300'
                                            }`}
                                          >
                                            {isChosen && <div className="h-1.5 w-1.5 rounded-full bg-white" />}
                                          </div>
                                          <span>{opt}</span>
                                        </div>
                                      </button>
                                    );
                                  })}
                                </div>
                              </div>
                            );
                          })()}

                          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-gray-100">
                            <div className="flex items-center space-x-3">
                              <button
                                onClick={() => setCurrentMcqIndex((prev) => Math.max(prev - 1, 0))}
                                disabled={currentMcqIndex === 0}
                                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-xs font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-2xs transition"
                              >
                                ◀ Previous
                              </button>
                              <button
                                onClick={() =>
                                  setCurrentMcqIndex((prev) =>
                                    Math.min(prev + 1, activeQuiz.questions.length - 1)
                                  )
                                }
                                disabled={currentMcqIndex === activeQuiz.questions.length - 1}
                                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-xs font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-2xs transition"
                              >
                                Next ▶
                              </button>
                            </div>

                            <button
                              onClick={handleQuizSubmit}
                              disabled={submittingQuiz}
                              className="w-full sm:w-auto rounded-lg bg-indigo-600 text-white px-6 py-2.5 text-xs font-bold hover:bg-indigo-700 shadow-md disabled:opacity-50 transition"
                            >
                              {submittingQuiz ? 'Submitting...' : 'Submit Quiz'}
                            </button>
                          </div>

                          <p className="text-3xs text-gray-400 text-center">
                            Note: You can submit the quiz even if some questions are left unanswered. 
                            Unanswered questions will simply be marked incorrect.
                          </p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-6">
                      <div className="bg-indigo-600 text-white rounded-2xl p-6 text-center shadow-md relative overflow-hidden">
                        <div className="absolute -top-12 -left-12 w-32 h-32 bg-white/10 rounded-full blur-2xl"></div>
                        <div className="relative">
                          <h3 className="text-xs uppercase tracking-widest font-semibold text-indigo-200">
                            Quiz Completed
                          </h3>
                          <div className="text-3xl md:text-4xl font-black mt-1">
                            {Math.round(quizResult.score * 100)}%
                          </div>
                          <p className="text-xs text-indigo-155 text-indigo-150 mt-1">
                            Score: <strong>{quizResult.correct_count}</strong> / {quizResult.questions_count} correct
                          </p>
                          <button
                            onClick={() => triggerMCQGeneration(true)}
                            className="mt-4 inline-flex items-center rounded-lg bg-white/20 hover:bg-white/30 text-white px-4 py-1.5 text-xs font-bold transition"
                          >
                            Retake New Quiz
                          </button>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                          Review Answers
                        </h4>

                        <div className="space-y-3">
                          {quizResult.feedback.map((feed, fIdx) => {
                            const originalQ = activeQuiz.questions.find((q) => q.id === feed.question_id);
                            const studentAnsIdx = feed.student_answer ? parseInt(feed.student_answer) : null;
                            const correctAnsIdx = parseInt(feed.correct_answer);

                            return (
                              <div
                                key={feed.question_id}
                                className={`rounded-xl border p-4 text-left shadow-2xs ${
                                  feed.is_correct
                                    ? 'bg-green-50/20 border-green-200'
                                    : 'bg-red-50/20 border-red-200'
                                }`}
                              >
                                <div className="flex justify-between items-center text-3xs font-bold uppercase tracking-wider mb-2">
                                  <span className="text-gray-400">Question {fIdx + 1}</span>
                                  <span
                                    className={`px-2 py-0.5 rounded-full ${
                                      feed.is_correct
                                        ? 'bg-green-100 text-green-800'
                                        : 'bg-red-100 text-red-800'
                                    }`}
                                  >
                                    {feed.is_correct ? 'Correct' : 'Incorrect'}
                                  </span>
                                </div>
                                <h5 className="text-xs md:text-sm font-bold text-gray-900 mb-3">
                                  {feed.question_text}
                                </h5>

                                <div className="space-y-1.5">
                                  {originalQ?.options.map((opt, oIdx) => {
                                    const isCorrectOpt = oIdx === correctAnsIdx;
                                    const isStudentChosen = oIdx === studentAnsIdx;

                                    return (
                                      <div
                                        key={oIdx}
                                        className={`px-3 py-2 rounded-lg border text-2xs md:text-xs font-semibold ${
                                          isCorrectOpt
                                            ? 'bg-green-100 border-green-300 text-green-900'
                                            : isStudentChosen
                                            ? 'bg-red-100 border-red-300 text-red-900'
                                            : 'bg-white border-gray-200 text-gray-600'
                                        }`}
                                      >
                                        <div className="flex items-center justify-between">
                                          <span>{opt}</span>
                                          {isCorrectOpt && (
                                            <span className="text-green-700 font-bold">✔ Correct Answer</span>
                                          )}
                                          {isStudentChosen && !isCorrectOpt && (
                                            <span className="text-red-700 font-bold">✘ Your Choice</span>
                                          )}
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            /* TAB 5: Short Answer Quiz Interface */
            <div className="flex-grow flex flex-col overflow-hidden bg-gray-50/30">
              
              {!activeSaQuiz && !saLoading && (
                <div className="flex-grow flex flex-col items-center justify-center p-8 text-center">
                  <h3 className="text-base font-bold text-gray-900">Short-Answer Quiz Not Generated</h3>
                  <p className="text-xs text-gray-500 mt-2 max-w-xs leading-relaxed">
                    Test your understanding with active writing. Submit short answers to be graded against course materials.
                  </p>

                  {saError && (
                    <div className="mt-4 max-w-sm rounded-md bg-red-50 p-3 text-xs text-red-700 border border-red-200">
                      {saError}
                    </div>
                  )}

                  <button
                    onClick={() => triggerSAGeneration(false)}
                    className="mt-5 rounded-lg bg-indigo-600 text-white px-5 py-2.5 text-xs font-bold hover:bg-indigo-700 shadow-md transition"
                  >
                    Generate Short-Answer Quiz
                  </button>
                </div>
              )}

              {saLoading && (
                <div className="flex-grow flex flex-col items-center justify-center p-8 text-center">
                  <svg className="animate-spin h-10 w-10 text-indigo-600 mb-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <h4 className="text-sm font-bold text-gray-900">Formulating Short Questions...</h4>
                  <p className="text-2xs text-gray-500 mt-1">Creating essay-style test questions requiring sentence answers...</p>
                </div>
              )}

              {activeSaQuiz && !saLoading && (
                <div className="flex-grow flex flex-col p-6 justify-between overflow-y-auto">
                  <div className="bg-white border rounded-xl p-3 flex justify-between items-center flex-shrink-0 text-xs shadow-2xs mb-4">
                    <span className="font-semibold text-gray-800">
                      Quiz Mode: Written Short-Answer Test
                    </span>
                    <button
                      onClick={() => triggerSAGeneration(true)}
                      className="text-2xs text-indigo-600 hover:text-indigo-850 font-bold hover:underline"
                    >
                      Regenerate Quiz
                    </button>
                  </div>

                  {saError && (
                    <div className="mb-4 rounded-md bg-red-50 p-3 text-xs text-red-700 border border-red-200">
                      ⚠️ {saError}
                    </div>
                  )}

                  {!saQuizResult ? (
                    <div className="flex-grow flex flex-col justify-between">
                      {activeSaQuiz.questions.length === 0 ? (
                        <div className="text-center py-12 text-gray-500 text-xs italic">
                          No questions generated for this document.
                        </div>
                      ) : (
                        <div className="space-y-6">
                          {(() => {
                            const q = activeSaQuiz.questions[currentSaIndex];
                            const studentAnsText = saAnswers[q.id] || '';

                            return (
                              <div className="space-y-4">
                                <div className="flex justify-between items-center text-3xs font-bold uppercase tracking-wider text-gray-400">
                                  <span>Concept: {q.topic}</span>
                                  <span>Question {currentSaIndex + 1} of {activeSaQuiz.questions.length}</span>
                                </div>
                                <h3 className="text-sm md:text-base font-bold text-gray-900 leading-normal">
                                  {q.question}
                                </h3>

                                <div className="pt-2">
                                  <label htmlFor={`sa-input-${q.id}`} className="sr-only">
                                    Your Answer
                                  </label>
                                  <textarea
                                    id={`sa-input-${q.id}`}
                                    rows={4}
                                    placeholder="Type your answer in 1-3 sentences..."
                                    value={studentAnsText}
                                    onChange={(e) => handleSaTextChange(q.id, e.target.value)}
                                    className="block w-full rounded-xl border border-gray-300 px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                                  />
                                </div>
                              </div>
                            );
                          })()}

                          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-gray-100">
                            <div className="flex items-center space-x-3">
                              <button
                                onClick={() => setCurrentSaIndex((prev) => Math.max(prev - 1, 0))}
                                disabled={currentSaIndex === 0}
                                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-xs font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-2xs transition"
                              >
                                ◀ Previous
                              </button>
                              <button
                                onClick={() =>
                                  setCurrentSaIndex((prev) =>
                                    Math.min(prev + 1, activeSaQuiz.questions.length - 1)
                                  )
                                }
                                disabled={currentSaIndex === activeSaQuiz.questions.length - 1}
                                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-xs font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-2xs transition"
                              >
                                Next ▶
                              </button>
                            </div>

                            <button
                              onClick={handleSaQuizSubmit}
                              disabled={submittingSaQuiz}
                              className="w-full sm:w-auto rounded-lg bg-indigo-600 text-white px-6 py-2.5 text-xs font-bold hover:bg-indigo-700 shadow-md disabled:opacity-50 transition"
                            >
                              {submittingSaQuiz ? 'Submitting...' : 'Submit Quiz'}
                            </button>
                          </div>

                          <p className="text-3xs text-gray-400 text-center">
                            Note: You can submit the quiz even with blank fields. Unanswered items will simply be marked incorrect.
                          </p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-6">
                      <div className="bg-indigo-600 text-white rounded-2xl p-6 text-center shadow-md relative overflow-hidden">
                        <div className="absolute -top-12 -left-12 w-32 h-32 bg-white/10 rounded-full blur-2xl"></div>
                        <div className="relative">
                          <h3 className="text-xs uppercase tracking-widest font-semibold text-indigo-200">
                            Quiz Completed (Keyword Graded)
                          </h3>
                          <div className="text-3xl md:text-4xl font-black mt-1">
                            {Math.round(saQuizResult.score * 100)}%
                          </div>
                          <p className="text-xs text-indigo-150 mt-1">
                            Score: <strong>{saQuizResult.correct_count}</strong> / {saQuizResult.questions_count} correct
                          </p>
                          <button
                            onClick={() => triggerSAGeneration(true)}
                            className="mt-4 inline-flex items-center rounded-lg bg-white/20 hover:bg-white/30 text-white px-4 py-1.5 text-xs font-bold transition"
                          >
                            Retake New Quiz
                          </button>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">
                          Review Written Answers
                        </h4>

                        <div className="space-y-4">
                          {saQuizResult.feedback.map((feed, fIdx) => {
                            return (
                              <div
                                key={feed.question_id}
                                className={`rounded-xl border p-4 text-left shadow-2xs space-y-3 ${
                                  feed.is_correct
                                    ? 'bg-green-50/20 border-green-200'
                                    : 'bg-red-50/20 border-red-200'
                                }`}
                              >
                                <div className="flex justify-between items-center text-3xs font-bold uppercase tracking-wider">
                                  <span className="text-gray-400">Question {fIdx + 1}</span>
                                  <span
                                    className={`px-2 py-0.5 rounded-full ${
                                      feed.is_correct
                                        ? 'bg-green-100 text-green-800'
                                        : 'bg-red-100 text-red-800'
                                    }`}
                                  >
                                    {feed.is_correct ? 'Correct' : 'Incorrect'}
                                  </span>
                                </div>
                                <h5 className="text-xs md:text-sm font-bold text-gray-900">
                                  {feed.question_text}
                                </h5>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                                  <div className="bg-white p-3 rounded-lg border border-gray-200">
                                    <div className="text-3xs font-bold uppercase tracking-wider text-gray-400 mb-1">
                                      Your Answer
                                    </div>
                                    <p className={`text-2xs md:text-xs leading-normal ${
                                      feed.student_answer ? 'text-gray-800' : 'text-gray-400 italic'
                                    }`}>
                                      {feed.student_answer || '(Empty Submission)'}
                                    </p>
                                  </div>

                                  <div className="bg-indigo-50/30 p-3 rounded-lg border border-indigo-100">
                                    <div className="text-3xs font-bold uppercase tracking-wider text-indigo-500 mb-1">
                                      Model Reference Answer
                                    </div>
                                    <p className="text-2xs md:text-xs text-indigo-900 leading-normal font-semibold">
                                      {feed.correct_answer}
                                    </p>
                                  </div>
                                </div>

                                <div className="text-3xs text-gray-400 leading-relaxed italic bg-white/40 p-2 rounded border border-gray-100 mt-2">
                                  * Note: Written answers are graded using case-insensitive keyword inclusion. 
                                  Please compare your response to the Model Reference Answer above to judge your accuracy.
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

        </div>

        {/* SECTION 3: Quiz History Dashboard (Full Width) */}
        <section className="bg-white rounded-2xl p-6 shadow-md border border-gray-100">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold text-gray-900">Quiz Performance History</h2>
            <button
              onClick={fetchQuizHistory}
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-850"
            >
              Refresh History
            </button>
          </div>

          {loadingHistory && historyList.length === 0 ? (
            <div className="text-center py-8 text-sm text-gray-500">Loading performance records...</div>
          ) : historyList.length === 0 ? (
            <div className="text-center py-12 text-sm text-gray-500 border-2 border-dashed border-gray-200 rounded-xl bg-gray-50/30">
              No quizzes attempted yet — generate one from a document above to get started!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Document
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Quiz Type
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Score
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Attempted At
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {historyList.map((hist, idx) => {
                    const pctScore = Math.round(hist.score * 100);
                    return (
                      <tr key={idx} className="hover:bg-gray-50 transition">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                          {hist.document_filename}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 uppercase">
                          {hist.quiz_type === 'mcq' ? 'Multiple Choice' : 'Short Answer'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-bold">
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs ${
                              hist.score >= 0.7
                                ? 'bg-green-100 text-green-800'
                                : hist.score >= 0.4
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {pctScore}%
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(hist.attempted_at).toLocaleString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

      </div>
      ) : (
        /* VIEW 2: My Progress (Analytics Dashboard) */
        <div className="flex-grow mx-auto max-w-7xl w-full px-4 py-8 sm:px-6 lg:px-8 space-y-8 overflow-y-auto">
          
          <div className="flex justify-between items-center pb-4 border-b border-gray-200">
            <div>
              <h1 className="text-2xl font-bold text-gray-950">My Learning Progress</h1>
              <p className="text-xs text-gray-500">Real-time weak topic aggregation and AI-guided study recommendations.</p>
            </div>
            <button
              onClick={fetchAnalytics}
              disabled={loadingAnalytics}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-xs font-bold text-indigo-600 hover:bg-gray-50 transition"
            >
              {loadingAnalytics ? 'Loading...' : '↻ Refresh Analytics'}
            </button>
          </div>

          {analyticsError && (
            <div className="rounded-md bg-red-50 p-4 text-sm text-red-700 border border-red-200">
              {analyticsError}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            
            {/* Left Panel: Weak Topics List (7 Cols) */}
            <div className="lg:col-span-7 bg-white rounded-2xl p-6 shadow-md border border-gray-100">
              <h2 className="text-lg font-bold text-gray-900 mb-4">Topic Accuracy Breakdown</h2>
              
              {loadingAnalytics && weakTopics.length === 0 ? (
                <div className="text-center py-12 text-sm text-gray-500">Loading topic analytics...</div>
              ) : weakTopics.length === 0 ? (
                <div className="text-center py-12 text-sm text-gray-500 border-2 border-dashed border-gray-200 rounded-xl bg-gray-50/20">
                  No topic performance data available yet. 
                  <p className="text-2xs text-gray-400 mt-2">
                    Tip: Complete quizzes with at least 3 questions per topic to populate analysis reports!
                  </p>
                </div>
              ) : (
                <div className="space-y-5">
                  {weakTopics.map((wt, idx) => {
                    const isWeak = wt.accuracy_percentage < 50;
                    const isAverage = wt.accuracy_percentage >= 50 && wt.accuracy_percentage < 75;
                    const colorClass = isWeak
                      ? 'bg-red-500'
                      : isAverage
                      ? 'bg-yellow-500'
                      : 'bg-green-500';

                    return (
                      <div key={idx} className="space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-semibold text-gray-800">{wt.topic}</span>
                          <span className="text-gray-500 font-medium">
                            {wt.correct_count} / {wt.total_attempted} answers correct ({wt.accuracy_percentage}%)
                          </span>
                        </div>
                        {/* Progress bar visual */}
                        <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                          <div
                            className={`h-2.5 rounded-full ${colorClass} transition-all`}
                            style={{ width: `${wt.accuracy_percentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Right Panel: Recommendations (5 Cols) */}
            <div className="lg:col-span-5 bg-white rounded-2xl p-6 shadow-md border border-gray-100 flex flex-col justify-between">
              <div>
                <h2 className="text-lg font-bold text-gray-900 mb-4">What to Revise Next</h2>
                
                {loadingAnalytics && recommendations.length === 0 ? (
                  <div className="text-center py-12 text-sm text-gray-500">Loading recommendations...</div>
                ) : recommendations.length === 0 ? (
                  <div className="text-center py-12 text-sm text-gray-500 border-2 border-dashed border-gray-200 rounded-xl bg-gray-50/20">
                    No active study recommendations.
                    <p className="text-2xs text-gray-400 mt-2">
                      Complete quiz tests to flag weak concepts and get targeted slide guides.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {recommendations.map((rec, idx) => (
                      <div key={idx} className="bg-indigo-50/40 p-4 rounded-xl border border-indigo-100 flex flex-col justify-between gap-3">
                        <div>
                          <span className="inline-flex px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800 text-3xs font-bold uppercase tracking-wider">
                            Topic: {rec.topic}
                          </span>
                          <p className="text-xs text-gray-700 font-semibold mt-2">
                            {rec.reason}
                          </p>
                        </div>
                        <div className="flex justify-between items-center border-t border-indigo-100/50 pt-2.5 mt-1">
                          <span className="text-3xs text-gray-400 truncate max-w-[150px]">
                            File: {rec.document_filename}
                          </span>
                          <button
                            onClick={() => handleRecommendationClick(rec.document_id)}
                            className="text-3xs font-black text-indigo-650 hover:text-indigo-850 hover:underline uppercase tracking-wider"
                          >
                            Open Slides ↗
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              <div className="mt-6 bg-gray-50 p-4 rounded-xl border border-gray-150 border-gray-200 text-3xs text-gray-400 leading-normal">
                * Note: Topics are calculated strictly from your graded quiz attempt history. 
                Topics with fewer than 3 total question attempts are ignored to ensure accurate tracking.
              </div>
            </div>

          </div>

        </div>
      )}
    </div>
  );
};

export default Dashboard;
