import React, { useState, useRef, useCallback } from 'react'; // 1. Import useCallback
import { useSearchParams } from 'react-router-dom';
import CameraFeed from './CameraFeed';
import FeedbackDisplay from './FeedbackDisplay';
import OverlayCanvas from './OverlayCanvas';
import useCPRWebSocket from '../hooks/useCPRWebSocket';

function CPRView() {
  const [searchParams] = useSearchParams();
  const videoRef = useRef(null);
  
  const mode = searchParams.get('mode') || 'feedback';

  const [feedback, setFeedback] = useState({
    bpm: 0,
    count: 0,
    message: "Initializing...",
  });

  // 2. Stabilize the onMessage function with useCallback
  // This tells React to use the *exact same function* on every render.
  // This is the key to breaking the re-render loop.
  const onSocketMessage = useCallback((data) => {
    setFeedback(data); // Update state with data from backend
  }, []); // The empty array [] means this function is created ONCE.

  // 3. Pass the new, stable function to our hook
  useCPRWebSocket({
    videoRef,
    onMessage: onSocketMessage
  });

  const renderWalkthroughUI = () => (
    <div className="walkthrough-controls">
      <p>Step 1: Check for responsiveness.</p>
      <button className="skip-button">Skip to Compressions</button>
    </div>
  );

  return (
    <div className="cpr-view-container">
      <FeedbackDisplay
        bpm={feedback.bpm}
        count={feedback.count}
        message={feedback.message}
      />
      {/* The CameraFeed will no longer be interrupted because
        this parent component will stop re-rendering.
      */}
      <CameraFeed ref={videoRef} />
      <OverlayCanvas />
      {mode === 'walkthrough' && renderWalkthroughUI()}
    </div>
  );
}

export default CPRView;