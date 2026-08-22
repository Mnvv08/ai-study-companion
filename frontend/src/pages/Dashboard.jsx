import React, { useContext, useState, useEffect, useRef } from 'react';
import { AuthContext } from '../context/AuthContext';
import apiClient from '../api/client';
import AppNavbar from '../components/AppNavbar';
import {
  Spinner,
  LoadingPane,
  ErrorBanner,
  SuccessBanner,
  EmptyState,
  ScoreBadge,
} from '../components/ui';

/* ─── helpers ─────────────────────────────────────────────── */
function PanelTab({ id, label, active, onClick }) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`panel-tab ${active ? 'panel-tab-active' : 'panel-tab-inactive'}`}
    >
      {label}
    </button>
  );
}

function QuizLoadingPane({ label }) {
  return (
    <div className="flex-grow flex flex-col items-center justify-center p-10 text-center">
      <Spinner size="lg" />
      <p className="mt-4 text-sm font-semibold text-gray-700">{label}</p>
      <p className="text-xs text-gray-400 mt-1">This takes 5–15 seconds.</p>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════ */
export default function Dashboard() {
  const { user } = useContext(AuthContext);

  /* view: 'workspace' | 'analytics' | 'settings' */
  const [currentView, setCurrentView] = useState('workspace');

  /* ── document state ── */
  const [documents, setDocuments]     = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [loadingList, setLoadingList] = useState(false);

  /* ── upload state ── */
  const [file, setFile]               = useState(null);
  const [uploading, setUploading]     = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');

  /* ── inner tab ── */
  const [activeTab, setActiveTab] = useState('chat');

  /* ── chat ── */
  const [chatHistory, setChatHistory] = useState([]);
  const [question, setQuestion]       = useState('');
  const [asking, setAsking]           = useState(false);
  const chatEndRef = useRef(null);

  /* ── notes ── */
  const [sessionNotes, setSessionNotes]       = useState({});
  const [notesLoading, setNotesLoading]       = useState(false);
  const [notesError, setNotesError]           = useState('');
  const [expandedSections, setExpandedSections] = useState({});

  /* ── flashcards ── */
  const [sessionFlashcards, setSessionFlashcards] = useState({});
  const [flashcardsLoading, setFlashcardsLoading] = useState(false);
  const [flashcardsError, setFlashcardsError]     = useState('');
  const [currentCardIndex, setCurrentCardIndex]   = useState(0);
  const [flipped, setFlipped]                     = useState(false);
  const [topicFilter, setTopicFilter]             = useState('All');

  /* ── MCQ ── */
  const [sessionMCQs, setSessionMCQs]   = useState({});
  const [mcqsLoading, setMcqsLoading]   = useState(false);
  const [mcqsError, setMcqsError]       = useState('');
  const [currentMcqIndex, setCurrentMcqIndex] = useState(0);
  const [mcqAnswers, setMcqAnswers]     = useState({});
  const [quizResult, setQuizResult]     = useState(null);
  const [submittingQuiz, setSubmittingQuiz] = useState(false);

  /* ── Short Answer ── */
  const [sessionSA, setSessionSA]       = useState({});
  const [saLoading, setSaLoading]       = useState(false);
  const [saError, setSaError]           = useState('');
  const [currentSaIndex, setCurrentSaIndex] = useState(0);
  const [saAnswers, setSaAnswers]       = useState({});
  const [saResult, setSaResult]         = useState(null);
  const [submittingSa, setSubmittingSa] = useState(false);

  /* ── quiz history ── */
  const [historyList, setHistoryList]     = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  /* ── analytics ── */
  const [weakTopics, setWeakTopics]         = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [analyticsError, setAnalyticsError]     = useState('');

  /* ── settings / persona ── */
  const [personaMode, setPersonaMode]         = useState(false);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsSaving, setSettingsSaving]   = useState(false);
  const [settingsError, setSettingsError]     = useState('');
  const [settingsSaved, setSettingsSaved]     = useState(false);

  /* ─── data loaders ──────────────────────────────────────── */
  const fetchDocuments = async () => {
    setLoadingList(true);
    try {
      const res = await apiClient.get('/documents');
      setDocuments(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingList(false);
    }
  };

  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await apiClient.get('/quizzes/history');
      setHistoryList(res.data);
    } catch (err) {
      console.error(err);
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
      setAnalyticsError(err.response?.data?.detail || 'Failed to load analytics.');
    } finally {
      setLoadingAnalytics(false);
    }
  };

  const fetchSettings = async () => {
    setSettingsLoading(true);
    setSettingsError('');
    try {
      const res = await apiClient.get('/users/me/settings');
      setPersonaMode(res.data.persona_mode);
    } catch (err) {
      setSettingsError('Failed to load settings.');
    } finally {
      setSettingsLoading(false);
    }
  };

  /* ─── mount ─────────────────────────────────────────────── */
  useEffect(() => {
    fetchDocuments();
    fetchHistory();
    fetchSettings();
  }, []);

  /* fetch analytics when entering My Progress */
  useEffect(() => {
    if (currentView === 'analytics') fetchAnalytics();
  }, [currentView]);

  /* ─── pending document polling ──────────────────────────── */
  const pendingIds = documents.filter((d) => d.status === 'pending').map((d) => d.id);
  useEffect(() => {
    if (!pendingIds.length) return;
    const timers = pendingIds.map((id) =>
      setInterval(async () => {
        try {
          const res = await apiClient.get(`/documents/${id}/status`);
          if (res.data.status !== 'pending') {
            setDocuments((prev) =>
              prev.map((d) => (d.id === id ? { ...d, status: res.data.status } : d))
            );
          }
        } catch {}
      }, 3000)
    );
    return () => timers.forEach(clearInterval);
  }, [pendingIds.join(',')]);

  /* ─── clear panel on doc change ─────────────────────────── */
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
    setSaResult(null);
    setActiveTab('chat');
  }, [selectedDocId]);

  /* scroll chat to bottom */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, asking]);

  /* ─── handlers ──────────────────────────────────────────── */
  const handleFileChange = (e) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0]);
      setUploadError('');
      setUploadSuccess('');
    }
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!file) return setUploadError('Please select a file first.');
    setUploading(true);
    setUploadError('');
    setUploadSuccess('');
    const fd = new FormData();
    fd.append('file', file);
    try {
      await apiClient.post('/documents/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setUploadSuccess(`"${file.name}" uploaded successfully!`);
      setFile(null);
      e.target.reset();
      const res = await apiClient.get('/documents');
      setDocuments(res.data);
    } catch (err) {
      setUploadError(err.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleAskSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim() || !selectedDocId) return;
    const q = question.trim();
    setQuestion('');
    setAsking(true);
    const idx = chatHistory.length;
    setChatHistory((prev) => [...prev, { question: q, answer: null, error: null, loading: true }]);
    try {
      const res = await apiClient.post('/qa/ask', { document_id: selectedDocId, question: q });
      setChatHistory((prev) =>
        prev.map((m, i) => (i === idx ? { ...m, answer: res.data.answer, loading: false } : m))
      );
    } catch (err) {
      const msg =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        'Network error — please try again.';
      setChatHistory((prev) =>
        prev.map((m, i) => (i === idx ? { ...m, error: msg, loading: false } : m))
      );
    } finally {
      setAsking(false);
    }
  };

  const triggerNotes = async (force = false) => {
    setNotesLoading(true);
    setNotesError('');
    try {
      const res = await apiClient.post('/notes/generate', {
        document_id: selectedDocId,
        force_regenerate: force,
      });
      setSessionNotes((prev) => ({ ...prev, [selectedDocId]: res.data }));
      const init = {};
      res.data.sections?.forEach((_, i) => { init[i] = i === 0; });
      setExpandedSections(init);
    } catch (err) {
      setNotesError(err.response?.data?.detail || 'Failed to generate notes.');
    } finally {
      setNotesLoading(false);
    }
  };

  const triggerFlashcards = async (force = false) => {
    setFlashcardsLoading(true);
    setFlashcardsError('');
    setCurrentCardIndex(0);
    setFlipped(false);
    setTopicFilter('All');
    try {
      const res = await apiClient.post('/flashcards/generate', {
        document_id: selectedDocId,
        force_regenerate: force,
      });
      setSessionFlashcards((prev) => ({ ...prev, [selectedDocId]: res.data.flashcards }));
    } catch (err) {
      setFlashcardsError(err.response?.data?.detail || 'Failed to generate flashcards.');
    } finally {
      setFlashcardsLoading(false);
    }
  };

  const triggerMCQs = async (force = false) => {
    setMcqsLoading(true);
    setMcqsError('');
    setCurrentMcqIndex(0);
    setMcqAnswers({});
    setQuizResult(null);
    try {
      const res = await apiClient.post('/mcqs/generate', {
        document_id: selectedDocId,
        force_regenerate: force,
      });
      setSessionMCQs((prev) => ({
        ...prev,
        [selectedDocId]: { quiz_id: res.data.quiz_id, questions: res.data.questions },
      }));
    } catch (err) {
      setMcqsError(err.response?.data?.detail || 'Failed to generate MCQ quiz.');
    } finally {
      setMcqsLoading(false);
    }
  };

  const handleMcqSubmit = async () => {
    const quiz = sessionMCQs[selectedDocId];
    if (!quiz) return;
    setSubmittingQuiz(true);
    setMcqsError('');
    try {
      const res = await apiClient.post(`/quizzes/${quiz.quiz_id}/submit`, {
        answers: quiz.questions.map((q) => ({
          question_id: q.id,
          student_answer: mcqAnswers[q.id] !== undefined ? String(mcqAnswers[q.id]) : '',
        })),
      });
      setQuizResult(res.data);
      fetchHistory();
      fetchAnalytics();
    } catch (err) {
      setMcqsError(err.response?.data?.detail || 'Failed to submit quiz.');
    } finally {
      setSubmittingQuiz(false);
    }
  };

  const triggerSA = async (force = false) => {
    setSaLoading(true);
    setSaError('');
    setCurrentSaIndex(0);
    setSaAnswers({});
    setSaResult(null);
    try {
      const res = await apiClient.post('/short-answer/generate', {
        document_id: selectedDocId,
        force_regenerate: force,
      });
      setSessionSA((prev) => ({
        ...prev,
        [selectedDocId]: { quiz_id: res.data.quiz_id, questions: res.data.questions },
      }));
    } catch (err) {
      setSaError(err.response?.data?.detail || 'Failed to generate short-answer quiz.');
    } finally {
      setSaLoading(false);
    }
  };

  const handleSaSubmit = async () => {
    const quiz = sessionSA[selectedDocId];
    if (!quiz) return;
    setSubmittingSa(true);
    setSaError('');
    try {
      const res = await apiClient.post(`/quizzes/${quiz.quiz_id}/submit`, {
        answers: quiz.questions.map((q) => ({
          question_id: q.id,
          student_answer: (saAnswers[q.id] || '').trim(),
        })),
      });
      setSaResult(res.data);
      fetchHistory();
      fetchAnalytics();
    } catch (err) {
      setSaError(err.response?.data?.detail || 'Failed to submit quiz.');
    } finally {
      setSubmittingSa(false);
    }
  };

  const handlePersonaToggle = async () => {
    const newVal = !personaMode;
    setSettingsSaving(true);
    setSettingsError('');
    setSettingsSaved(false);
    try {
      const res = await apiClient.patch('/users/me/settings', { persona_mode: newVal });
      setPersonaMode(res.data.persona_mode);
      setSettingsSaved(true);
      setTimeout(() => setSettingsSaved(false), 3000);
    } catch (err) {
      setSettingsError(err.response?.data?.detail || 'Failed to save setting.');
    } finally {
      setSettingsSaving(false);
    }
  };

  const handleRecommendationClick = (docId) => {
    if (docId && docId !== 'unknown') {
      setSelectedDocId(docId);
      setCurrentView('workspace');
      setActiveTab('notes');
    }
  };

  /* ─── computed values ───────────────────────────────────── */
  const currentNotes  = sessionNotes[selectedDocId];
  const allCards      = sessionFlashcards[selectedDocId] || [];
  const activeMcqQuiz = sessionMCQs[selectedDocId];
  const activeSaQuiz  = sessionSA[selectedDocId];
  const selectedDocName = documents.find((d) => d.id === selectedDocId)?.filename;

  const uniqueTopics = ['All', ...new Set(allCards.map((c) => c.topic))];
  const filteredCards =
    topicFilter === 'All' ? allCards : allCards.filter((c) => c.topic === topicFilter);
  const displayCard = filteredCards[currentCardIndex];

  /* ─────────────────────────── RENDER ───────────────────── */
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <AppNavbar
        currentView={currentView}
        onViewChange={setCurrentView}
        personaMode={personaMode}
      />

      {/* ═══ WORKSPACE VIEW ═══════════════════════════════ */}
      {currentView === 'workspace' && (
        <div className="flex-grow mx-auto max-w-7xl w-full px-4 py-8 sm:px-6 lg:px-8 space-y-8">

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

            {/* ── Left column: upload + document list ── */}
            <div className="lg:col-span-5 space-y-6 flex flex-col">

              {/* Upload */}
              <section className="card flex-shrink-0">
                <h2 className="section-title mb-4">Upload Study Material</h2>
                <SuccessBanner message={uploadSuccess} className="mb-4" />
                <ErrorBanner  message={uploadError}   className="mb-4" />
                <form onSubmit={handleUploadSubmit} className="space-y-3">
                  <input
                    type="file"
                    accept=".pdf,.pptx,.ppt"
                    onChange={handleFileChange}
                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"
                  />
                  <button
                    type="submit"
                    disabled={uploading || !file}
                    className="btn-primary w-full"
                  >
                    {uploading ? <><Spinner size="sm" className="mr-2" />Uploading…</> : 'Upload File'}
                  </button>
                  <p className="text-xs text-gray-400 text-center">PDF, PPTX, PPT · max 20 MB</p>
                </form>
              </section>

              {/* Document list */}
              <section className="card flex-grow flex flex-col min-h-[280px]">
                <div className="flex justify-between items-center mb-4 flex-shrink-0">
                  <h2 className="section-title">Your Documents</h2>
                  <button onClick={fetchDocuments} className="btn-ghost text-xs text-indigo-600">
                    ↻ Refresh
                  </button>
                </div>

                <div className="flex-grow overflow-y-auto max-h-[380px]">
                  {loadingList && !documents.length ? (
                    <div className="text-center py-8 text-sm text-gray-400">Loading…</div>
                  ) : !documents.length ? (
                    <EmptyState body="No documents uploaded yet." />
                  ) : (
                    <ul className="space-y-2.5">
                      {documents.map((doc) => {
                        const isSelected  = selectedDocId === doc.id;
                        const isReady     = doc.status === 'processed';
                        return (
                          <li
                            key={doc.id}
                            onClick={() => isReady && setSelectedDocId(doc.id)}
                            className={`card-sm transition ${
                              isReady ? 'cursor-pointer' : 'opacity-60 cursor-not-allowed'
                            } ${
                              isSelected ? 'ring-2 ring-indigo-500 border-indigo-300 bg-indigo-50' : 'hover:bg-gray-50'
                            }`}
                          >
                            <div className="flex justify-between items-start gap-2">
                              <span className="font-semibold text-sm text-gray-900 truncate">{doc.filename}</span>
                              <span className={`status-badge ${
                                doc.status === 'processed' ? 'bg-green-50 text-green-700 border border-green-200'
                                : doc.status === 'failed'  ? 'bg-red-50 text-red-700 border border-red-200'
                                : 'bg-yellow-50 text-yellow-700 border border-yellow-200 animate-pulse'
                              }`}>
                                {doc.status}
                              </span>
                            </div>
                            <div className="flex justify-between mt-1.5 text-xs text-gray-400">
                              <span>{doc.file_type}</span>
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

            {/* ── Right column: feature tabs panel ── */}
            <div className="lg:col-span-7 bg-white rounded-2xl shadow-md border border-gray-100 flex flex-col min-h-[500px] overflow-hidden">

              {/* Panel header */}
              <div className="bg-gray-50 border-b border-gray-200 px-4 py-3 flex-shrink-0">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                  {[
                    ['chat',         'Q&A Chat'],
                    ['notes',        'Notes'],
                    ['flashcards',   'Flashcards'],
                    ['mcqs',         'MCQ Quiz'],
                    ['short_answer', 'Short-Answer'],
                  ].map(([id, label]) => (
                    <PanelTab
                      key={id}
                      id={id}
                      label={label}
                      active={activeTab === id}
                      onClick={!selectedDocId ? () => {} : setActiveTab}
                    />
                  ))}
                </div>
                {selectedDocId ? (
                  <div className="flex items-center justify-between mt-1.5">
                    <p className="text-xs text-gray-400 truncate">📄 {selectedDocName}</p>
                    <button
                      onClick={() => setSelectedDocId(null)}
                      className="text-xs text-red-500 hover:text-red-700 font-semibold ml-2 flex-shrink-0"
                    >
                      ✕ Clear
                    </button>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400 mt-1">Select a document to activate study tools</p>
                )}
              </div>

              {/* Panel body */}
              {!selectedDocId ? (
                <div className="flex-grow flex flex-col items-center justify-center p-10 text-center bg-gray-50/50">
                  <div className="w-16 h-16 rounded-full bg-indigo-50 flex items-center justify-center text-4xl mb-4">🎓</div>
                  <h3 className="font-bold text-gray-800">No Document Selected</h3>
                  <p className="text-sm text-gray-500 mt-2 max-w-xs leading-relaxed">
                    Choose a processed document from the list to start chatting, generating notes, flashcards, or quizzes.
                  </p>
                </div>

              ) : activeTab === 'chat' ? (
                /* TAB: Q&A Chat */
                <div className="flex-grow flex flex-col overflow-hidden">
                  <div className="flex-grow p-4 overflow-y-auto space-y-3">
                    {!chatHistory.length && !asking && (
                      <p className="text-center py-16 text-xs text-gray-400 italic">
                        Ask anything about the selected document…
                      </p>
                    )}
                    {chatHistory.map((msg, i) => {
                      const isRefusal = msg.answer === "I couldn't find this in your uploaded material.";
                      return (
                        <div key={i} className="space-y-2">
                          <div className="flex justify-end">
                            <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-sm text-sm shadow-sm">
                              {msg.question}
                            </div>
                          </div>
                          <div className="flex justify-start">
                            {msg.loading ? (
                              <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-2.5 flex items-center gap-2 text-sm text-gray-500">
                                <span className="relative flex h-2 w-2">
                                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75" />
                                  <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500" />
                                </span>
                                Thinking…
                              </div>
                            ) : msg.error ? (
                              <div className="alert-error rounded-2xl rounded-tl-sm max-w-sm">
                                <strong className="block text-xs uppercase tracking-wider mb-1">Error</strong>
                                {msg.error}
                              </div>
                            ) : (
                              <div className={`rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-sm text-sm leading-relaxed shadow-sm ${
                                isRefusal
                                  ? 'bg-gray-50 text-gray-500 italic border border-gray-200'
                                  : 'bg-gray-100 text-gray-800'
                              }`}>
                                {msg.answer}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                    <div ref={chatEndRef} />
                  </div>
                  <form onSubmit={handleAskSubmit} className="p-3 bg-gray-50 border-t border-gray-200 flex gap-2 flex-shrink-0">
                    <input
                      type="text"
                      required
                      placeholder="Ask a question about the document…"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      disabled={asking}
                      className="form-input flex-grow"
                    />
                    <button type="submit" disabled={asking || !question.trim()} className="btn-primary px-5">
                      Ask
                    </button>
                  </form>
                </div>

              ) : activeTab === 'notes' ? (
                /* TAB: Notes */
                <div className="flex-grow flex flex-col overflow-hidden">
                  {!currentNotes && !notesLoading && (
                    <div className="flex-grow flex flex-col items-center justify-center p-10 text-center">
                      <EmptyState
                        title="Notes Not Generated"
                        body="Convert this document into structured headings, bullet points, and key terms."
                        action={
                          <button onClick={() => triggerNotes(false)} className="btn-primary">
                            Generate Notes
                          </button>
                        }
                      />
                      <ErrorBanner message={notesError} className="mt-4 max-w-sm" />
                    </div>
                  )}
                  {notesLoading && <QuizLoadingPane label="Structuring study notes…" />}
                  {currentNotes && !notesLoading && (
                    <div className="flex-grow flex flex-col overflow-hidden">
                      <div className="flex justify-between items-center px-4 py-2 bg-white border-b border-gray-100 text-xs flex-shrink-0">
                        <span className="font-semibold text-gray-700">{currentNotes.title || 'Study Notes'}</span>
                        <button onClick={() => triggerNotes(true)} className="text-indigo-600 hover:underline font-semibold">
                          ↺ Regenerate
                        </button>
                      </div>
                      <ErrorBanner message={notesError} className="mx-4 mt-2" />
                      <div className="flex-grow flex flex-col md:flex-row overflow-hidden">
                        {/* Sections */}
                        <div className="flex-grow md:w-3/5 p-4 overflow-y-auto space-y-3">
                          {currentNotes.sections?.map((sec, i) => (
                            <div key={i} className="rounded-xl border border-gray-200 overflow-hidden">
                              <button
                                onClick={() => setExpandedSections((p) => ({ ...p, [i]: !p[i] }))}
                                className="w-full text-left px-4 py-3 bg-gray-50 hover:bg-gray-100 flex justify-between items-center text-sm font-bold text-gray-900 border-b border-gray-100 transition"
                              >
                                <span>{sec.heading}</span>
                                <span className="text-xs text-gray-400 font-normal">{expandedSections[i] ? '▲' : '▼'}</span>
                              </button>
                              {expandedSections[i] && (
                                <ul className="p-4 space-y-1.5 list-disc list-inside text-xs text-gray-700 leading-relaxed bg-white">
                                  {sec.points?.map((pt, j) => <li key={j}>{pt}</li>)}
                                </ul>
                              )}
                            </div>
                          ))}
                        </div>
                        {/* Key terms sidebar */}
                        <div className="md:w-2/5 bg-gray-50 border-t md:border-t-0 md:border-l border-gray-200 p-4 overflow-y-auto">
                          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Key Terms</h3>
                          {!currentNotes.key_terms?.length ? (
                            <p className="text-xs text-gray-400 italic">No key terms listed.</p>
                          ) : (
                            <ul className="space-y-3">
                              {currentNotes.key_terms.map((t, i) => (
                                <li key={i} className="card-sm">
                                  <div className="font-bold text-xs text-indigo-700">{t.term}</div>
                                  <div className="text-xs text-gray-600 mt-1 leading-normal">{t.definition}</div>
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
                /* TAB: Flashcards */
                <div className="flex-grow flex flex-col overflow-hidden">
                  {!allCards.length && !flashcardsLoading && (
                    <div className="flex-grow flex flex-col items-center justify-center p-10 text-center">
                      <EmptyState
                        title="Flashcards Not Generated"
                        body="Create active-recall flip cards from this document."
                        action={
                          <button onClick={() => triggerFlashcards(false)} className="btn-primary">
                            Generate Flashcards
                          </button>
                        }
                      />
                      <ErrorBanner message={flashcardsError} className="mt-4 max-w-sm" />
                    </div>
                  )}
                  {flashcardsLoading && <QuizLoadingPane label="Creating flashcards…" />}
                  {allCards.length > 0 && !flashcardsLoading && (
                    <div className="flex-grow flex flex-col p-6 overflow-y-auto">
                      {/* Controls */}
                      <div className="flex justify-between items-center mb-6">
                        <div className="flex items-center gap-2">
                          <label className="text-xs font-semibold text-gray-600">Topic:</label>
                          <select
                            value={topicFilter}
                            onChange={(e) => { setTopicFilter(e.target.value); setCurrentCardIndex(0); setFlipped(false); }}
                            className="text-xs rounded-md border border-gray-300 bg-white px-2 py-1 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                          >
                            {uniqueTopics.map((t, i) => <option key={i} value={t}>{t}</option>)}
                          </select>
                        </div>
                        <button onClick={() => triggerFlashcards(true)} className="text-xs text-indigo-600 hover:underline font-semibold">
                          ↺ Regenerate
                        </button>
                      </div>
                      <ErrorBanner message={flashcardsError} className="mb-4" />

                      {!filteredCards.length ? (
                        <p className="text-center py-10 text-xs text-gray-400 italic">No cards match this topic.</p>
                      ) : (
                        <div className="flex flex-col items-center gap-6">
                          {/* Card */}
                          <div
                            onClick={() => setFlipped(!flipped)}
                            className={`w-full max-w-md min-h-[180px] flex flex-col justify-between p-6 rounded-2xl border cursor-pointer select-none transition-all shadow-md ${
                              flipped
                                ? 'bg-indigo-50 border-indigo-300 ring-4 ring-indigo-500/10'
                                : 'bg-white border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            <div className="flex justify-between text-xs font-bold uppercase tracking-wider text-gray-400">
                              <span>{displayCard.topic}</span>
                              <span className={flipped ? 'text-indigo-600' : ''}>{flipped ? 'Answer' : 'Question'}</span>
                            </div>
                            <div className="py-4 text-center">
                              <p className={`text-sm font-bold leading-relaxed ${flipped ? 'text-gray-700 font-normal' : 'text-gray-900'}`}>
                                {flipped ? displayCard.back : displayCard.front}
                              </p>
                            </div>
                            <p className="text-center text-xs text-gray-400">
                              {flipped ? 'Click to show question' : 'Click to flip'}
                            </p>
                          </div>
                          {/* Progress & nav */}
                          <p className="text-xs font-semibold text-gray-500">
                            Card {currentCardIndex + 1} of {filteredCards.length}
                          </p>
                          <div className="flex gap-3">
                            <button
                              onClick={() => { setFlipped(false); setCurrentCardIndex((p) => Math.max(p - 1, 0)); }}
                              disabled={currentCardIndex === 0}
                              className="btn-secondary text-xs px-4 py-2"
                            >◀ Prev</button>
                            <button
                              onClick={() => { setFlipped(false); setCurrentCardIndex((p) => Math.min(p + 1, filteredCards.length - 1)); }}
                              disabled={currentCardIndex === filteredCards.length - 1}
                              className="btn-secondary text-xs px-4 py-2"
                            >Next ▶</button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

              ) : activeTab === 'mcqs' ? (
                /* TAB: MCQ Quiz */
                <div className="flex-grow flex flex-col overflow-hidden">
                  {!activeMcqQuiz && !mcqsLoading && (
                    <div className="flex-grow flex flex-col items-center justify-center p-10 text-center">
                      <EmptyState
                        title="MCQ Quiz Not Generated"
                        body="Test your understanding with dynamically generated multiple-choice questions."
                        action={
                          <button onClick={() => triggerMCQs(false)} className="btn-primary">
                            Generate MCQ Quiz
                          </button>
                        }
                      />
                      <ErrorBanner message={mcqsError} className="mt-4 max-w-sm" />
                    </div>
                  )}
                  {mcqsLoading && <QuizLoadingPane label="Generating MCQ quiz…" />}
                  {activeMcqQuiz && !mcqsLoading && (
                    <div className="flex-grow flex flex-col p-6 overflow-y-auto space-y-5">
                      {/* Subheader */}
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-gray-700">MCQ Practice Test</span>
                        <button onClick={() => triggerMCQs(true)} className="text-xs text-indigo-600 hover:underline font-semibold">↺ Regenerate</button>
                      </div>
                      <ErrorBanner message={mcqsError} />

                      {!quizResult ? (
                        /* Taking quiz */
                        (() => {
                          const q = activeMcqQuiz.questions[currentMcqIndex];
                          const chosen = mcqAnswers[q.id];
                          return (
                            <div className="space-y-5">
                              <div className="flex justify-between text-xs font-bold uppercase tracking-wider text-gray-400">
                                <span>{q.topic}</span>
                                <span>Q{currentMcqIndex + 1} / {activeMcqQuiz.questions.length}</span>
                              </div>
                              <p className="text-sm font-bold text-gray-900 leading-normal">{q.question}</p>
                              <div className="space-y-2.5">
                                {q.options.map((opt, oi) => {
                                  const sel = chosen === oi;
                                  return (
                                    <button
                                      key={oi}
                                      onClick={() => setMcqAnswers((p) => ({ ...p, [q.id]: oi }))}
                                      className={`w-full text-left px-4 py-3 rounded-xl border text-sm font-semibold transition ${
                                        sel ? 'bg-indigo-50 border-indigo-400 ring-2 ring-indigo-500/10 text-indigo-900'
                                            : 'bg-white border-gray-200 hover:bg-gray-50 text-gray-700'
                                      }`}
                                    >
                                      <span className={`inline-flex h-4 w-4 rounded-full border mr-3 items-center justify-center flex-shrink-0 ${sel ? 'border-indigo-600 bg-indigo-600' : 'border-gray-300'}`}>
                                        {sel && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
                                      </span>
                                      {opt}
                                    </button>
                                  );
                                })}
                              </div>
                              <div className="flex items-center justify-between pt-4 border-t border-gray-100">
                                <div className="flex gap-2">
                                  <button onClick={() => setCurrentMcqIndex((p) => Math.max(p - 1, 0))} disabled={currentMcqIndex === 0} className="btn-secondary text-xs px-3 py-2">◀ Prev</button>
                                  <button onClick={() => setCurrentMcqIndex((p) => Math.min(p + 1, activeMcqQuiz.questions.length - 1))} disabled={currentMcqIndex === activeMcqQuiz.questions.length - 1} className="btn-secondary text-xs px-3 py-2">Next ▶</button>
                                </div>
                                <button onClick={handleMcqSubmit} disabled={submittingQuiz} className="btn-primary text-xs px-5 py-2">
                                  {submittingQuiz ? 'Submitting…' : 'Submit Quiz'}
                                </button>
                              </div>
                              <p className="text-xs text-gray-400 text-center">Unanswered questions count as incorrect.</p>
                            </div>
                          );
                        })()
                      ) : (
                        /* Results */
                        <div className="space-y-6">
                          <div className="bg-indigo-600 text-white rounded-2xl p-6 text-center relative overflow-hidden shadow-md">
                            <div className="absolute -top-10 -left-10 w-32 h-32 bg-white/10 rounded-full blur-2xl" />
                            <div className="relative">
                              <p className="text-xs uppercase tracking-widest text-indigo-200">Quiz Complete</p>
                              <p className="text-4xl font-black mt-1">{Math.round(quizResult.score * 100)}%</p>
                              <p className="text-xs text-indigo-200 mt-1">{quizResult.correct_count} / {quizResult.questions_count} correct</p>
                              <button onClick={() => triggerMCQs(true)} className="mt-4 inline-flex btn-ghost text-white hover:bg-white/20 text-xs px-4 py-1.5">Retake New Quiz</button>
                            </div>
                          </div>
                          <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Review Answers</h4>
                          <div className="space-y-3">
                            {quizResult.feedback.map((feed, fi) => {
                              const origQ = activeMcqQuiz.questions.find((q) => q.id === feed.question_id);
                              const stuIdx = feed.student_answer !== '' ? parseInt(feed.student_answer) : null;
                              const corIdx = parseInt(feed.correct_answer);
                              return (
                                <div key={fi} className={`rounded-xl border p-4 ${feed.is_correct ? 'bg-green-50/30 border-green-200' : 'bg-red-50/30 border-red-200'}`}>
                                  <div className="flex justify-between text-xs font-bold uppercase tracking-wider mb-2">
                                    <span className="text-gray-400">Q{fi + 1}</span>
                                    <span className={feed.is_correct ? 'score-badge-green' : 'score-badge-red'}>{feed.is_correct ? '✓ Correct' : '✗ Incorrect'}</span>
                                  </div>
                                  <p className="text-sm font-bold text-gray-900 mb-3">{feed.question_text}</p>
                                  <div className="space-y-1.5">
                                    {origQ?.options.map((opt, oi) => {
                                      const isRight = oi === corIdx, isChosen = oi === stuIdx;
                                      return (
                                        <div key={oi} className={`px-3 py-2 rounded-lg border text-xs font-semibold flex justify-between ${
                                          isRight ? 'bg-green-100 border-green-300 text-green-900'
                                          : isChosen ? 'bg-red-100 border-red-300 text-red-900'
                                          : 'bg-white border-gray-200 text-gray-600'
                                        }`}>
                                          <span>{opt}</span>
                                          {isRight  && <span className="text-green-700 font-bold">✔ Correct</span>}
                                          {isChosen && !isRight && <span className="text-red-700 font-bold">✘ Yours</span>}
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

              ) : (
                /* TAB: Short Answer */
                <div className="flex-grow flex flex-col overflow-hidden">
                  {!activeSaQuiz && !saLoading && (
                    <div className="flex-grow flex flex-col items-center justify-center p-10 text-center">
                      <EmptyState
                        title="Short-Answer Quiz Not Generated"
                        body="Write short answers graded against the document's content."
                        action={
                          <button onClick={() => triggerSA(false)} className="btn-primary">
                            Generate Short-Answer Quiz
                          </button>
                        }
                      />
                      <ErrorBanner message={saError} className="mt-4 max-w-sm" />
                    </div>
                  )}
                  {saLoading && <QuizLoadingPane label="Generating short-answer quiz…" />}
                  {activeSaQuiz && !saLoading && (
                    <div className="flex-grow flex flex-col p-6 overflow-y-auto space-y-5">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-semibold text-gray-700">Written Short-Answer Test</span>
                        <button onClick={() => triggerSA(true)} className="text-xs text-indigo-600 hover:underline font-semibold">↺ Regenerate</button>
                      </div>
                      <ErrorBanner message={saError} />

                      {!saResult ? (
                        (() => {
                          const q = activeSaQuiz.questions[currentSaIndex];
                          return (
                            <div className="space-y-5">
                              <div className="flex justify-between text-xs font-bold uppercase tracking-wider text-gray-400">
                                <span>{q.topic}</span>
                                <span>Q{currentSaIndex + 1} / {activeSaQuiz.questions.length}</span>
                              </div>
                              <p className="text-sm font-bold text-gray-900 leading-normal">{q.question}</p>
                              <textarea
                                rows={4}
                                placeholder="Type your answer in 1–3 sentences…"
                                value={saAnswers[q.id] || ''}
                                onChange={(e) => setSaAnswers((p) => ({ ...p, [q.id]: e.target.value }))}
                                className="form-textarea"
                              />
                              <div className="flex items-center justify-between pt-4 border-t border-gray-100">
                                <div className="flex gap-2">
                                  <button onClick={() => setCurrentSaIndex((p) => Math.max(p - 1, 0))} disabled={currentSaIndex === 0} className="btn-secondary text-xs px-3 py-2">◀ Prev</button>
                                  <button onClick={() => setCurrentSaIndex((p) => Math.min(p + 1, activeSaQuiz.questions.length - 1))} disabled={currentSaIndex === activeSaQuiz.questions.length - 1} className="btn-secondary text-xs px-3 py-2">Next ▶</button>
                                </div>
                                <button onClick={handleSaSubmit} disabled={submittingSa} className="btn-primary text-xs px-5 py-2">
                                  {submittingSa ? 'Submitting…' : 'Submit Quiz'}
                                </button>
                              </div>
                              <p className="text-xs text-gray-400 text-center">Blank answers count as incorrect.</p>
                            </div>
                          );
                        })()
                      ) : (
                        /* SA Results */
                        <div className="space-y-6">
                          <div className="bg-indigo-600 text-white rounded-2xl p-6 text-center relative overflow-hidden shadow-md">
                            <div className="absolute -top-10 -left-10 w-32 h-32 bg-white/10 rounded-full blur-2xl" />
                            <div className="relative">
                              <p className="text-xs uppercase tracking-widest text-indigo-200">Quiz Complete · Keyword Graded</p>
                              <p className="text-4xl font-black mt-1">{Math.round(saResult.score * 100)}%</p>
                              <p className="text-xs text-indigo-200 mt-1">{saResult.correct_count} / {saResult.questions_count} correct</p>
                              <button onClick={() => triggerSA(true)} className="mt-4 inline-flex btn-ghost text-white hover:bg-white/20 text-xs px-4 py-1.5">Retake New Quiz</button>
                            </div>
                          </div>
                          <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Review Written Answers</h4>
                          <div className="space-y-4">
                            {saResult.feedback.map((feed, fi) => (
                              <div key={fi} className={`rounded-xl border p-4 space-y-3 ${feed.is_correct ? 'bg-green-50/30 border-green-200' : 'bg-red-50/30 border-red-200'}`}>
                                <div className="flex justify-between text-xs font-bold uppercase tracking-wider">
                                  <span className="text-gray-400">Q{fi + 1}</span>
                                  <span className={feed.is_correct ? 'score-badge-green' : 'score-badge-red'}>{feed.is_correct ? '✓ Correct' : '✗ Incorrect'}</span>
                                </div>
                                <p className="text-sm font-bold text-gray-900">{feed.question_text}</p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                  <div className="card-sm">
                                    <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">Your Answer</p>
                                    <p className={`text-xs leading-normal ${feed.student_answer ? 'text-gray-800' : 'text-gray-400 italic'}`}>
                                      {feed.student_answer || '(empty)'}
                                    </p>
                                  </div>
                                  <div className="bg-indigo-50/50 p-3 rounded-xl border border-indigo-100">
                                    <p className="text-xs font-bold uppercase tracking-wider text-indigo-500 mb-1">Model Answer</p>
                                    <p className="text-xs text-indigo-900 leading-normal font-semibold">{feed.correct_answer}</p>
                                  </div>
                                </div>
                                <p className="text-xs text-gray-400 italic">
                                  * Graded by keyword match — compare to model answer to assess your understanding.
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Quiz History table */}
          <section className="card">
            <div className="flex justify-between items-center mb-4">
              <h2 className="section-title">Quiz Performance History</h2>
              <button onClick={fetchHistory} className="btn-ghost text-xs text-indigo-600">↻ Refresh</button>
            </div>
            {loadingHistory && !historyList.length ? (
              <div className="text-center py-8 text-sm text-gray-400">Loading…</div>
            ) : !historyList.length ? (
              <EmptyState body="No quizzes attempted yet — generate one from a document above to get started!" />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      {['Document', 'Quiz Type', 'Score', 'Attempted At'].map((h) => (
                        <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-100">
                    {historyList.map((h, i) => (
                      <tr key={i} className="hover:bg-gray-50 transition">
                        <td className="px-5 py-3 text-sm font-semibold text-gray-900">{h.document_filename}</td>
                        <td className="px-5 py-3 text-sm text-gray-500">{h.quiz_type === 'mcq' ? 'Multiple Choice' : 'Short Answer'}</td>
                        <td className="px-5 py-3"><ScoreBadge score={h.score} /></td>
                        <td className="px-5 py-3 text-sm text-gray-500">{new Date(h.attempted_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}

      {/* ═══ ANALYTICS VIEW ═══════════════════════════════ */}
      {currentView === 'analytics' && (
        <div className="flex-grow mx-auto max-w-7xl w-full px-4 py-8 sm:px-6 lg:px-8 space-y-8">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">My Learning Progress</h1>
              <p className="section-subtitle">Weak-topic breakdown from graded quiz history · recommendations sorted weakest first</p>
            </div>
            <button onClick={fetchAnalytics} disabled={loadingAnalytics} className="btn-secondary text-xs">
              {loadingAnalytics ? <><Spinner size="sm" className="mr-1.5" />Loading…</> : '↻ Refresh'}
            </button>
          </div>

          <ErrorBanner message={analyticsError} />

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Weak topics */}
            <div className="lg:col-span-7 card space-y-5">
              <h2 className="section-title">Topic Accuracy Breakdown</h2>
              {loadingAnalytics && !weakTopics.length ? (
                <LoadingPane label="Analysing quiz history…" />
              ) : !weakTopics.length ? (
                <EmptyState
                  body="No topic data yet. Complete quizzes with ≥ 3 questions per topic to see results here."
                />
              ) : (
                <div className="space-y-5">
                  {weakTopics.map((wt, i) => {
                    const pct = wt.accuracy_percentage;
                    const barColor = pct < 50 ? 'bg-red-500' : pct < 75 ? 'bg-yellow-500' : 'bg-green-500';
                    return (
                      <div key={i} className="space-y-1.5">
                        <div className="flex justify-between text-sm">
                          <span className="font-semibold text-gray-800">{wt.topic}</span>
                          <span className="text-gray-500 text-xs">
                            {wt.correct_count}/{wt.total_attempted} correct &nbsp;·&nbsp; <strong>{pct}%</strong>
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                          <div
                            className={`h-2.5 rounded-full ${barColor} transition-all duration-500`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Recommendations */}
            <div className="lg:col-span-5 card flex flex-col gap-4">
              <h2 className="section-title">What to Revise Next</h2>
              {loadingAnalytics && !recommendations.length ? (
                <LoadingPane label="Loading recommendations…" />
              ) : !recommendations.length ? (
                <EmptyState body="No recommendations yet. Complete more quizzes to unlock targeted study suggestions." />
              ) : (
                recommendations.map((rec, i) => (
                  <div key={i} className="bg-indigo-50/40 border border-indigo-100 rounded-xl p-4 flex flex-col gap-2">
                    <span className="inline-flex px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800 text-xs font-bold uppercase tracking-wider w-fit">
                      {rec.topic}
                    </span>
                    <p className="text-sm text-gray-700 font-medium">{rec.reason}</p>
                    <div className="flex justify-between items-center border-t border-indigo-100 pt-2 mt-1 text-xs">
                      <span className="text-gray-400 truncate">{rec.document_filename}</span>
                      <button
                        onClick={() => handleRecommendationClick(rec.document_id)}
                        className="text-indigo-600 font-bold hover:underline ml-2 flex-shrink-0"
                      >
                        Open Notes ↗
                      </button>
                    </div>
                  </div>
                ))
              )}
              <div className="mt-auto pt-4 border-t border-gray-100 text-xs text-gray-400 leading-relaxed">
                Topics with fewer than 3 question attempts are excluded to avoid statistical noise.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ═══ SETTINGS VIEW ════════════════════════════════ */}
      {currentView === 'settings' && (
        <div className="flex-grow mx-auto max-w-2xl w-full px-4 py-10 sm:px-6 space-y-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
            <p className="section-subtitle">Personalise your AI Study Companion experience.</p>
          </div>

          <section className="card space-y-6">
            <div>
              <h2 className="section-title">Mentor Persona</h2>
              <p className="text-sm text-gray-500 mt-1">
                Toggle Hinglish Mentor Mode to receive Q&amp;A answers, study notes, flashcards, MCQ feedback, and revision recommendations in a friendly Hinglish style (English mixed with casual Hindi).
              </p>
            </div>

            {settingsLoading ? (
              <LoadingPane label="Loading settings…" />
            ) : (
              <div className="flex items-center justify-between p-4 rounded-xl border border-gray-200 bg-gray-50">
                <div>
                  <p className="text-sm font-bold text-gray-900">🇮🇳 Hinglish Mentor Mode</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Currently: <strong className={personaMode ? 'text-orange-600' : 'text-gray-600'}>
                      {personaMode ? 'ON' : 'OFF'}
                    </strong>
                  </p>
                </div>
                <button
                  onClick={handlePersonaToggle}
                  disabled={settingsSaving}
                  aria-pressed={personaMode}
                  className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${
                    personaMode ? 'bg-indigo-600' : 'bg-gray-300'
                  } ${settingsSaving ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform ${
                      personaMode ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            )}

            <SuccessBanner message={settingsSaved ? 'Setting saved!' : ''} />
            <ErrorBanner  message={settingsError} />

            <div className="alert-info rounded-xl text-xs leading-relaxed">
              <strong>How this works:</strong> Persona mode is a server-side setting stored on your user account.
              Every subsequent LLM call (Q&amp;A, notes, flashcards, MCQs, short-answer, recommendations) automatically
              reads your current <code>persona_mode</code> flag — no changes needed to any individual feature page.
              Simply toggle here and generate or ask again.
            </div>
          </section>

          <section className="card space-y-4">
            <h2 className="section-title">Account</h2>
            <div className="flex justify-between items-center text-sm">
              <div>
                <p className="font-semibold text-gray-900">{user?.email || '—'}</p>
                <p className="text-gray-400 text-xs">Signed-in account</p>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
