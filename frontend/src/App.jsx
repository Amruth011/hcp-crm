import React, { useState, useRef, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { setInteraction, patchInteraction, clearInteraction } from './features/interactionSlice';
import './App.css';

// ── Lightweight markdown renderer (no external dep) ──────────────────────
function renderInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**'))
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('*') && part.endsWith('*'))
      return <em key={i}>{part.slice(1, -1)}</em>;
    if (part.startsWith('`') && part.endsWith('`'))
      return <code key={i}>{part.slice(1, -1)}</code>;
    return part;
  });
}

function SimpleMarkdown({ children }) {
  if (!children) return null;
  const lines = children.split('\n');
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block (``` or ```lang)
    if (/^```/.test(line)) {
      const codeLines = [];
      i++; // skip opening fence
      while (i < lines.length && !/^```/.test(lines[i])) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing fence
      out.push(
        <pre key={out.length} className="md-code-block">
          <code>{codeLines.join('\n')}</code>
        </pre>
      );
    } else if (/^[-*] /.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*] /.test(lines[i])) {
        items.push(lines[i].slice(2));
        i++;
      }
      out.push(<ul key={out.length}>{items.map((it, j) => <li key={j}>{renderInline(it)}</li>)}</ul>);
    } else if (/^\d+\. /.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+\. /.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\. /, ''));
        i++;
      }
      out.push(<ol key={out.length}>{items.map((it, j) => <li key={j}>{renderInline(it)}</li>)}</ol>);
    } else if (line.trim() === '') {
      i++;
    } else {
      out.push(<p key={out.length}>{renderInline(line)}</p>);
      i++;
    }
  }
  return <div className="md-content">{out}</div>;
}

function App() {
  const interaction = useSelector((state) => state.interaction);
  const dispatch = useDispatch();

  // Chat state
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const chatEndRef = useRef(null);
  const prevInteractionRef = useRef(interaction);
  const [changedFields, setChangedFields] = useState({});
  const [expandedTraces, setExpandedTraces] = useState(new Set());

  // Voice note and consent states
  const [hasVoiceConsent, setHasVoiceConsent] = useState(false);
  const [voiceConsentShowing, setVoiceConsentShowing] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingStatus, setRecordingStatus] = useState('');
  const recognitionRef = useRef(null);

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isLoading]);

  // Detect which fields changed due to a tool call and flash them for 4 s
  useEffect(() => {
    const prev = prevInteractionRef.current;
    const curr = interaction;
    const changes = {};

    const strFields = ['hcp_name', 'interaction_type', 'date', 'time',
                       'topics_discussed', 'sentiment', 'outcomes', 'follow_up_actions'];
    for (const f of strFields) {
      if (prev[f] !== curr[f] && prev[f] != null && prev[f] !== '') {
        changes[f] = { oldValue: String(prev[f]) };
      }
    }
    const arrFields = ['attendees', 'materials_shared', 'samples_distributed'];
    for (const f of arrFields) {
      const pv = prev[f] || [];
      const cv = curr[f] || [];
      if (JSON.stringify(pv) !== JSON.stringify(cv) && pv.length > 0) {
        changes[f] = { oldValue: pv.join(', ') };
      }
    }

    prevInteractionRef.current = curr;
    if (Object.keys(changes).length === 0) return;

    setChangedFields(ex => ({ ...ex, ...changes }));
    const t = setTimeout(() => {
      setChangedFields(ex => {
        const n = { ...ex };
        for (const k of Object.keys(changes)) delete n[k];
        return n;
      });
    }, 4000);
    return () => clearTimeout(t);
  }, [interaction]);

  const sendMessage = async (messageText) => {
    if (!messageText.trim() || isLoading) return;

    setErrorMsg('');
    setIsLoading(true);

    const updatedHistory = [...chatHistory, { role: 'user', content: messageText }];
    setChatHistory(updatedHistory);

    try {
      const backendHistory = updatedHistory.slice(0, -1).map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      const apiBaseUrl = import.meta.env.VITE_API_URL || (isLocalhost ? 'http://localhost:8000' : '');
      const response = await fetch(`${apiBaseUrl}/api/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageText,
          interaction_form: interaction,
          history: backendHistory,
        }),
      });

      if (!response.ok) throw new Error(`Server returned error status ${response.status}`);

      // Add placeholder assistant message
      setChatHistory(prev => [
        ...prev,
        { role: 'assistant', content: '', toolTrace: [] }
      ]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep last partial line

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.slice(6).trim();
            if (!dataStr) continue;
            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'patch') {
                dispatch(patchInteraction(data.interaction_form));
              } else if (data.type === 'tool_trace') {
                setChatHistory(prev => {
                  const next = [...prev];
                  const lastMsg = { ...next[next.length - 1] };
                  if (lastMsg.role === 'assistant') {
                    lastMsg.toolTrace = [
                      ...(lastMsg.toolTrace || []),
                      {
                        tool_name: data.tool_name,
                        input_data: data.input_data,
                        output_data: data.output_data,
                      }
                    ];
                    next[next.length - 1] = lastMsg;
                  }
                  return next;
                });
              } else if (data.type === 'message') {
                setChatHistory(prev => {
                  const next = [...prev];
                  const lastMsg = { ...next[next.length - 1] };
                  if (lastMsg.role === 'assistant') {
                    lastMsg.content = data.content;
                    next[next.length - 1] = lastMsg;
                  }
                  return next;
                });
              } else if (data.type === 'error') {
                setErrorMsg(data.detail || 'An error occurred during streaming.');
              }
            } catch (err) {
              console.error('Error parsing SSE JSON:', err);
            }
          }
        }
      }

      if (buffer.trim()) {
        const trimmed = buffer.trim();
        if (trimmed.startsWith('data: ')) {
          const dataStr = trimmed.slice(6).trim();
          if (dataStr) {
            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'patch') {
                dispatch(patchInteraction(data.interaction_form));
              } else if (data.type === 'tool_trace') {
                setChatHistory(prev => {
                  const next = [...prev];
                  const lastMsg = { ...next[next.length - 1] };
                  if (lastMsg.role === 'assistant') {
                    lastMsg.toolTrace = [
                      ...(lastMsg.toolTrace || []),
                      {
                        tool_name: data.tool_name,
                        input_data: data.input_data,
                        output_data: data.output_data,
                      }
                    ];
                    next[next.length - 1] = lastMsg;
                  }
                  return next;
                });
              } else if (data.type === 'message') {
                setChatHistory(prev => {
                  const next = [...prev];
                  const lastMsg = { ...next[next.length - 1] };
                  if (lastMsg.role === 'assistant') {
                    lastMsg.content = data.content;
                    next[next.length - 1] = lastMsg;
                  }
                  return next;
                });
              } else if (data.type === 'error') {
                setErrorMsg(data.detail || 'An error occurred during streaming.');
              }
            } catch (err) {
              console.error('Error parsing trailing buffer:', err);
            }
          }
        }
      }

      setChatHistory(prev => {
        const next = [...prev];
        const lastMsg = { ...next[next.length - 1] };
        if (lastMsg.role === 'assistant' && !lastMsg.content) {
          lastMsg.content = "I've updated the interaction details for you.";
          next[next.length - 1] = lastMsg;
        }
        return next;
      });

    } catch (err) {
      console.error('Error during chat request:', err);
      setErrorMsg('Failed to connect to the AI assistant. Please check if the backend is running.');
      setChatHistory(prev => {
        const next = [...prev];
        if (next.length > 0 && next[next.length - 1].role === 'assistant' && !next[next.length - 1].content && (!next[next.length - 1].toolTrace || next[next.length - 1].toolTrace.length === 0)) {
          next.pop();
        }
        return [
          ...next,
          { role: 'assistant', content: "Sorry, I encountered an error. Please try again.", toolTrace: [] }
        ];
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || isLoading) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    await sendMessage(userMessage);
  };

  const startVoiceRecording = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setRecordingStatus("Speech recognition not supported. Simulating voice note...");
      setIsRecording(true);
      setTimeout(() => {
        const mockTranscript = "Today I met with Dr. Smith and discussed product X efficacy. Sentiment was positive, I shared brochures.";
        sendMessage(mockTranscript);
        setIsRecording(false);
        setRecordingStatus("");
      }, 3000);
      return;
    }

    try {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = 'en-US';

      rec.onstart = () => {
        setIsRecording(true);
        setRecordingStatus("Listening... Speak now.");
      };

      rec.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        if (event.error === 'not-allowed') {
          setRecordingStatus("Microphone access denied. Please enable mic permissions.");
        } else {
          setRecordingStatus(`Error: ${event.error}. Try again.`);
        }
        setIsRecording(false);
      };

      rec.onend = () => {
        setIsRecording(false);
      };

      rec.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setRecordingStatus(`Transcribed: "${transcript}"`);
          sendMessage(transcript);
        } else {
          setRecordingStatus("No speech detected.");
        }
      };

      recognitionRef.current = rec;
      rec.start();
    } catch (err) {
      console.error("Failed to start speech recognition:", err);
      setRecordingStatus("Failed to start recording.");
      setIsRecording(false);
    }
  };

  const stopVoiceRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    } else {
      setIsRecording(false);
      setRecordingStatus("");
    }
  };

  const handleVoiceNoteClick = () => {
    if (!hasVoiceConsent) {
      setVoiceConsentShowing(true);
      setRecordingStatus("Consent required to access microphone.");
      return;
    }

    if (isRecording) {
      stopVoiceRecording();
    } else {
      startVoiceRecording();
    }
  };

  const handleReset = () => {
    dispatch(clearInteraction());
    setChatHistory([]);
    setErrorMsg('');
  };

  // Helper: renders the 4-second strikethrough hint below a changed field
  const ChgHint = ({ field }) => {
    if (!changedFields[field]) return null;
    return (
      <div className="change-hint">
        <span className="change-hint-old">{changedFields[field].oldValue}</span>
        <span className="change-hint-arrow">→</span>
      </div>
    );
  };

  const toggleTrace = (key) => {
    setExpandedTraces(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const INTERACTION_TYPES = ['Meeting', 'Call', 'Email', 'Conference', 'Demo', 'Visit', 'Webinar'];
  const itValue = interaction.interaction_type || '';
  const itOptions = INTERACTION_TYPES.includes(itValue)
    ? INTERACTION_TYPES
    : itValue ? [...INTERACTION_TYPES, itValue] : INTERACTION_TYPES;

  return (
    <div className="page-shell">
      <h1 className="page-title">Log HCP Interaction</h1>

      <div className="panels-row">
        {/* ── LEFT PANEL ──────────────────────────────────────────── */}
        <div className="left-panel">
          <p className="card-section-label">Interaction Details</p>

          <form className="crm-form" onSubmit={e => e.preventDefault()}>

            {/* 1. HCP Name + Interaction Type */}
            <div className="form-row">
              <div className="form-group flex-1">
                <label>HCP Name</label>
                <input
                  type="text"
                  value={interaction.hcp_name || ''}
                  readOnly disabled
                  placeholder="Search or select HCP..."
                />
                <ChgHint field="hcp_name" />
              </div>
              <div className="form-group flex-1">
                <label>Interaction Type</label>
                <div className="select-wrapper">
                  <select disabled value={itValue} onChange={() => {}}>
                    <option value="">Select type…</option>
                    {itOptions.map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                </div>
                <ChgHint field="interaction_type" />
              </div>
            </div>

            {/* 2. Date + Time */}
            <div className="form-row">
              <div className="form-group flex-1">
                <label>Date</label>
                <input
                  type="date"
                  value={interaction.date || ''}
                  readOnly disabled
                />
                <ChgHint field="date" />
              </div>
              <div className="form-group flex-1">
                <label>Time</label>
                <input
                  type="time"
                  value={interaction.time || ''}
                  readOnly disabled
                />
                <ChgHint field="time" />
              </div>
            </div>

            {/* 3. Attendees */}
            <div className="form-group">
              <label>Attendees</label>
              <input
                type="text"
                value={Array.isArray(interaction.attendees)
                  ? interaction.attendees.join(', ')
                  : (interaction.attendees || '')}
                readOnly disabled
                placeholder="Enter names or search..."
              />
              <ChgHint field="attendees" />
            </div>

            {/* 4. Topics Discussed */}
            <div className="form-group">
              <label>Topics Discussed</label>
              <div className="textarea-wrapper">
                <textarea
                  value={interaction.topics_discussed || ''}
                  readOnly disabled
                  placeholder="Enter key discussion points..."
                  rows={5}
                />
                <span className="mic-decoration">🎤</span>
              </div>
              <ChgHint field="topics_discussed" />

              {/* Voice Consent Checkbox */}
              {(voiceConsentShowing || !hasVoiceConsent) && (
                <div className="voice-consent-box">
                  <label className="voice-consent-label">
                    <input
                      type="checkbox"
                      id="voice-consent-checkbox"
                      checked={hasVoiceConsent}
                      onChange={(e) => {
                        setHasVoiceConsent(e.target.checked);
                        if (e.target.checked) {
                          setRecordingStatus('');
                        }
                      }}
                    />
                    <span>I consent to voice recording and transcription.</span>
                  </label>
                </div>
              )}

              <div className="voice-note-action-row">
                <button
                  type="button"
                  className={`voice-note-btn ${isRecording ? 'recording' : ''}`}
                  onClick={handleVoiceNoteClick}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className={isRecording ? 'pulse-icon' : ''}>
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                    <line x1="12" y1="19" x2="12" y2="23"/>
                    <line x1="8" y1="23" x2="16" y2="23"/>
                  </svg>
                  {isRecording ? 'Recording... Click to Stop' : 'Summarize from Voice Note'}
                </button>
                {recordingStatus && <span className="recording-status">{recordingStatus}</span>}
              </div>
            </div>

            {/* 5. Materials Shared / Samples Distributed – vertical stack */}
            <div className="form-group">
              <label className="section-label-bold">Materials Shared / Samples Distributed</label>

              <div className="material-box">
                <div className="material-box-header">
                  <span className="material-box-title">Materials Shared</span>
                  <button type="button" className="material-action-btn" disabled>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                    Search/Add
                  </button>
                </div>
                {interaction.materials_shared && interaction.materials_shared.length > 0 ? (
                  <div className="material-chips">
                    {interaction.materials_shared.map((m, i) => <span key={i} className="mat-chip">{m}</span>)}
                  </div>
                ) : (
                  <p className="material-empty">No materials added.</p>
                )}
                <ChgHint field="materials_shared" />
              </div>

              <div className="material-box">
                <div className="material-box-header">
                  <span className="material-box-title">Samples Distributed</span>
                  <button type="button" className="material-action-btn" disabled>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                    Add Sample
                  </button>
                </div>
                {interaction.samples_distributed && interaction.samples_distributed.length > 0 ? (
                  <div className="material-chips">
                    {interaction.samples_distributed.map((s, i) => <span key={i} className="mat-chip">{s}</span>)}
                  </div>
                ) : (
                  <p className="material-empty">No samples added.</p>
                )}
                <ChgHint field="samples_distributed" />
              </div>
            </div>

            {/* 6. Sentiment */}
            <div className="form-group">
              <label>Observed/Inferred HCP Sentiment</label>
              <div className="sentiment-row">
                {[
                  { value: 'positive', emoji: '😊', label: 'Positive' },
                  { value: 'neutral',  emoji: '😐', label: 'Neutral' },
                  { value: 'negative', emoji: '😢', label: 'Negative' },
                ].map(({ value, emoji, label }) => (
                  <label key={value} className={`sentiment-opt sentiment-opt-${value} ${interaction.sentiment === value ? 'is-checked' : ''}`}>
                    <input
                      type="radio"
                      name="sentiment"
                      value={value}
                      checked={interaction.sentiment === value}
                      disabled readOnly
                      onChange={() => {}}
                    />
                    <span className="sent-emoji">{emoji}</span>
                    {label}
                  </label>
                ))}
              </div>
            </div>

            {/* 7. Outcomes */}
            <div className="form-group">
              <label>Outcomes</label>
              <textarea
                value={interaction.outcomes || ''}
                readOnly disabled
                placeholder="Key outcomes or agreements..."
                rows={3}
              />
              <ChgHint field="outcomes" />
            </div>

            {/* 8. Follow-up Actions + AI Suggested Follow-ups */}
            <div className="form-group">
              <label>Follow-up Actions</label>
              <textarea
                value={interaction.follow_up_actions || ''}
                readOnly disabled
                placeholder="Enter next steps or tasks..."
                rows={3}
              />
              <ChgHint field="follow_up_actions" />

              <div className="suggested-followups-box">
                <p className="suggested-followups-label">AI Suggested Follow-ups:</p>
                <ul className="suggested-followups-list">
                  {interaction.suggested_follow_ups && interaction.suggested_follow_ups.length > 0 ? (
                    interaction.suggested_follow_ups.map((action, idx) => (
                      <li
                        key={idx}
                        onClick={() => {
                          const currentActions = interaction.follow_up_actions || '';
                          const newActions = currentActions
                            ? `${currentActions}\n- ${action}`
                            : `- ${action}`;
                          dispatch(patchInteraction({ follow_up_actions: newActions }));
                        }}
                        style={{ cursor: 'pointer' }}
                        title="Click to add to Follow-up Actions"
                      >
                        {action}
                      </li>
                    ))
                  ) : (
                    <li className="no-suggestions">No suggestions yet. Log topics and outcomes to get suggestions.</li>
                  )}
                </ul>
              </div>
            </div>

          </form>
        </div>

        {/* ── RIGHT PANEL ─────────────────────────────────────────── */}
        <div className="right-panel">

          {/* Header */}
          <div className="right-panel-header">
            <div className="ai-header-info">
              <div className="ai-header-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
              </div>
              <div>
                <h2 className="ai-header-title">AI Assistant</h2>
                <span className="ai-header-sub">Log interaction via chat</span>
              </div>
            </div>
            <button type="button" className="reset-btn" onClick={handleReset}>
              Reset Form
            </button>
          </div>

          {/* Compliance Banner */}
          {interaction.compliance_flag === 'review' && (
            <div className="compliance-warning-card">
              <div className="warning-header">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                <span>Compliance Review Suggested</span>
              </div>
              <p className="warning-detail">{interaction.compliance_rationale || 'Potential off-label claim detected.'}</p>
            </div>
          )}

          {/* Chat messages */}
          <div className="chat-messages-container">
            {/* Static pinned welcome bubble */}
            <div className="chat-bubble-wrapper assistant-message">
              <div className="chat-bubble welcome-bubble">
                <p>Log interaction details here (e.g., &ldquo;Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure&rdquo;) or ask for help.</p>
              </div>
            </div>

            {chatHistory.map((msg, index) => (
              <div key={index} className={`chat-bubble-wrapper ${msg.role === 'user' ? 'user-message' : 'assistant-message'}`}>
                <div className="chat-bubble">
                  {msg.role === 'user' ? (
                    <p>{msg.content}</p>
                  ) : (
                    <SimpleMarkdown>{msg.content}</SimpleMarkdown>
                  )}
                </div>

                {/* Tool trace tags */}
                {msg.role === 'assistant' && msg.toolTrace && msg.toolTrace.length > 0 && (
                  <div className="tool-trace-list">
                    {msg.toolTrace.map((trace, ti) => {
                      const key = `${index}-${ti}`;
                      return (
                        <div key={ti} className="tool-trace-item">
                          <button
                            className="tool-trace-tag"
                            onClick={() => toggleTrace(key)}
                            title="Click to inspect raw tool I/O"
                          >
                            <span className="tool-trace-icon">⚙</span>
                            {trace.tool_name}
                            <span className="tool-trace-chevron">{expandedTraces.has(key) ? '▲' : '▼'}</span>
                          </button>
                          {expandedTraces.has(key) && (
                            <pre className="tool-trace-detail">{JSON.stringify(
                              { input: trace.input_data, output: trace.output_data },
                              null, 2
                            )}</pre>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="chat-bubble-wrapper assistant-message">
                <div className="chat-bubble loading-bubble">
                  <span className="loading-dot" />
                  <span className="loading-dot" />
                  <span className="loading-dot" />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {errorMsg && <div className="chat-error-message">{errorMsg}</div>}

          {/* Input bar */}
          <form className="chat-input-form" onSubmit={handleSendMessage}>
            <input
              type="text"
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              placeholder="Describe interaction..."
              disabled={isLoading}
            />
            <button type="submit" className="log-btn" disabled={isLoading || !chatInput.trim()}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="12" y1="19" x2="12" y2="5"/>
                <polyline points="5 12 12 5 19 12"/>
              </svg>
              Log
            </button>
          </form>

        </div>
      </div>
    </div>
  );
}

export default App;
