import React, { useState, useRef, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { setInteraction, clearInteraction } from './features/interactionSlice';
import './App.css';

function App() {
  const interaction = useSelector((state) => state.interaction);
  const dispatch = useDispatch();

  // Chat state
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { role: 'assistant', content: "Hello! I am your AI Copilot. Speak or type to log or update interaction details." }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const chatEndRef = useRef(null);

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isLoading]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || isLoading) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setErrorMsg('');
    setIsLoading(true);

    // Update history locally with user message
    const updatedHistory = [...chatHistory, { role: 'user', content: userMessage }];
    setChatHistory(updatedHistory);

    try {
      // Map history format to FastAPI ChatRequest model
      const backendHistory = updatedHistory.slice(0, -1).map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          interaction_form: interaction,
          history: backendHistory,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned error status ${response.status}`);
      }

      const data = await response.json();
      
      // Update form state in Redux
      if (data.interaction_form) {
        dispatch(setInteraction(data.interaction_form));
      }

      // Add assistant response to history
      setChatHistory(prev => [
        ...prev,
        { role: 'assistant', content: data.chat_response || "I've updated the interaction details for you." }
      ]);
    } catch (err) {
      console.error('Error during chat request:', err);
      setErrorMsg('Failed to connect to the AI Copilot. Please check if the backend is running.');
      setChatHistory(prev => [
        ...prev,
        { role: 'assistant', content: "Sorry, I encountered an error communicating with the backend. Please try again." }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    dispatch(clearInteraction());
    setChatHistory([
      { role: 'assistant', content: "Interaction state reset. How can I help you log a new interaction?" }
    ]);
    setErrorMsg('');
  };

  return (
    <div className="app-container">
      {/* LEFT PANEL - Interaction Details Form (Disabled/Read-only) */}
      <div className="left-panel">
        <div className="panel-header">
          <h2>Interaction Details</h2>
          <span className="ai-lock-badge">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
            </svg>
            AI Managed
          </span>
        </div>

        <form className="crm-form" onSubmit={(e) => e.preventDefault()}>
          {/* 1. HCP Name + Interaction Type (same row) */}
          <div className="form-row">
            <div className="form-group flex-1">
              <label>HCP Name</label>
              <input
                type="text"
                value={interaction.hcp_name || ''}
                readOnly
                disabled
                placeholder="No HCP selected"
              />
            </div>
            <div className="form-group flex-1">
              <label>Interaction Type</label>
              <input
                type="text"
                value={interaction.interaction_type || ''}
                readOnly
                disabled
                placeholder="e.g. Call, Meeting"
              />
            </div>
          </div>

          {/* 2. Date + Time (same row) */}
          <div className="form-row">
            <div className="form-group flex-1">
              <label>Date</label>
              <input
                type="text"
                value={interaction.date || ''}
                readOnly
                disabled
                placeholder="YYYY-MM-DD"
              />
            </div>
            <div className="form-group flex-1">
              <label>Time</label>
              <input
                type="text"
                value={interaction.time || ''}
                readOnly
                disabled
                placeholder="HH:MM AM/PM"
              />
            </div>
          </div>

          {/* 3. Attendees */}
          <div className="form-group">
            <label>Attendees</label>
            <div className="chips-container">
              {interaction.attendees && interaction.attendees.length > 0 ? (
                interaction.attendees.map((attendee, index) => (
                  <span key={index} className="chip">{attendee}</span>
                ))
              ) : (
                <span className="no-data-placeholder">No attendees recorded</span>
              )}
            </div>
          </div>

          {/* 4. Topics Discussed (textarea) + Summarize Link below it */}
          <div className="form-group">
            <label>Topics Discussed</label>
            <textarea
              value={interaction.topics_discussed || ''}
              readOnly
              disabled
              placeholder="No topics discussed recorded"
              rows={4}
            />
            <div className="consent-link-container">
              <a
                href="#"
                className="consent-link"
                onClick={(e) => {
                  e.preventDefault();
                  // No action as it requires voice consent flow
                }}
              >
                Summarize from Voice Note (Requires Consent)
              </a>
            </div>
          </div>

          {/* 5. Materials Shared and Samples Distributed as two separate sub-sections */}
          <div className="form-row sub-sections-row">
            {/* Materials Shared Sub-section */}
            <div className="sub-section flex-1">
              <div className="sub-section-header">
                <h4>Materials Shared</h4>
                <button type="button" className="action-btn" disabled>Search/Add</button>
              </div>
              <div className="chips-container">
                {interaction.materials_shared && interaction.materials_shared.length > 0 ? (
                  interaction.materials_shared.map((material, idx) => (
                    <span key={idx} className="chip secondary-chip">{material}</span>
                  ))
                ) : (
                  <span className="no-data-placeholder">No materials shared</span>
                )}
              </div>
            </div>

            {/* Samples Distributed Sub-section */}
            <div className="sub-section flex-1">
              <div className="sub-section-header">
                <h4>Samples Distributed</h4>
                <button type="button" className="action-btn" disabled>Add Sample</button>
              </div>
              <div className="chips-container">
                {interaction.samples_distributed && interaction.samples_distributed.length > 0 ? (
                  interaction.samples_distributed.map((sample, idx) => (
                    <span key={idx} className="chip secondary-chip">{sample}</span>
                  ))
                ) : (
                  <span className="no-data-placeholder">No samples distributed</span>
                )}
              </div>
            </div>
          </div>

          {/* 6. Observed/Inferred HCP Sentiment */}
          <div className="form-group">
            <label>Observed/Inferred HCP Sentiment</label>
            <div className="sentiment-radio-group">
              <label className={`sentiment-radio-label positive-label ${interaction.sentiment === 'positive' ? 'checked' : ''}`}>
                <input
                  type="radio"
                  name="sentiment"
                  value="positive"
                  checked={interaction.sentiment === 'positive'}
                  disabled
                  readOnly
                />
                <span className="sentiment-emoji">😊</span> Positive
              </label>

              <label className={`sentiment-radio-label neutral-label ${interaction.sentiment === 'neutral' ? 'checked' : ''}`}>
                <input
                  type="radio"
                  name="sentiment"
                  value="neutral"
                  checked={interaction.sentiment === 'neutral'}
                  disabled
                  readOnly
                />
                <span className="sentiment-emoji">😐</span> Neutral
              </label>

              <label className={`sentiment-radio-label negative-label ${interaction.sentiment === 'negative' ? 'checked' : ''}`}>
                <input
                  type="radio"
                  name="sentiment"
                  value="negative"
                  checked={interaction.sentiment === 'negative'}
                  disabled
                  readOnly
                />
                <span className="sentiment-emoji">🙁</span> Negative
              </label>
            </div>
          </div>

          {/* 7. Outcomes (textarea) */}
          <div className="form-group">
            <label>Outcomes</label>
            <textarea
              value={interaction.outcomes || ''}
              readOnly
              disabled
              placeholder="No outcomes recorded"
              rows={3}
            />
          </div>

          {/* 8. Follow-up Actions (textarea) + AI Suggested Follow-ups below it */}
          <div className="form-group">
            <label>Follow-up Actions</label>
            <textarea
              value={interaction.follow_up_actions || ''}
              readOnly
              disabled
              placeholder="No follow-up actions recorded"
              rows={3}
            />
            
            {/* AI Suggested Follow-ups as bulleted "+" list */}
            <div className="suggested-followups-box">
              <h5>AI Suggested Follow-ups</h5>
              <ul className="suggested-followups-list">
                {interaction.suggested_follow_ups && interaction.suggested_follow_ups.length > 0 ? (
                  interaction.suggested_follow_ups.map((action, idx) => (
                    <li key={idx}>{action}</li>
                  ))
                ) : (
                  <li className="no-suggestions">No suggestions compiled yet. Log topics and outcomes to get suggestions.</li>
                )}
              </ul>
            </div>
          </div>
        </form>
      </div>

      {/* RIGHT PANEL - AI Assistant Chat */}
      <div className="right-panel">
        <div className="panel-header">
          <h2>AI Copilot</h2>
          <button type="button" className="reset-btn" onClick={handleReset}>
            Reset Form
          </button>
        </div>

        {/* Compliance Banner if review is flagged */}
        {interaction.compliance_flag === 'review' && (
          <div className="compliance-warning-card">
            <div className="warning-header">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
              </svg>
              <span>Compliance Review Suggested</span>
            </div>
            <p className="warning-detail">{interaction.compliance_rationale || 'Potential off-label claim or exaggerated efficacy detected.'}</p>
          </div>
        )}

        <div className="chat-messages-container">
          {chatHistory.map((msg, index) => (
            <div key={index} className={`chat-bubble-wrapper ${msg.role === 'user' ? 'user-message' : 'assistant-message'}`}>
              <div className="chat-bubble">
                <p>{msg.content}</p>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="chat-bubble-wrapper assistant-message">
              <div className="chat-bubble loading-bubble">
                <span className="loading-dot"></span>
                <span className="loading-dot"></span>
                <span className="loading-dot"></span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {errorMsg && <div className="chat-error-message">{errorMsg}</div>}

        <form className="chat-input-form" onSubmit={handleSendMessage}>
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="Type your interaction details..."
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || !chatInput.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
