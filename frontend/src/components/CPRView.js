import React, { useState, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import CameraFeed from './CameraFeed';
import FeedbackDisplay from './FeedbackDisplay';
import OverlayCanvas from './OverlayCanvas';
import useCPRWebSocket from '../hooks/useCPRWebSocket';

function CPRView() {
  const [searchParams] = useSearchParams();
  const videoRef = useRef(null);
  
  const mode = searchParams.get('mode') || 'feedback';

  // --- NEW: State for camera direction ---
  const [facingMode, setFacingMode] = useState("user"); // 'user' = front, 'environment' = back

  const [feedback, setFeedback] = useState({
    bpm: 0,
    count: 0,
    message: "Initializing...",
  });

  const onSocketMessage = useCallback((data) => {
    setFeedback(data);
  }, []);

  useCPRWebSocket({
    videoRef,
    onMessage: onSocketMessage
  });

  // --- NEW: Function to flip the camera ---
  const toggleCamera = () => {
    setFacingMode((prevMode) => (prevMode === "user" ? "environment" : "user"));
  };

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
      
      {/* --- NEW: Button to flip camera --- */}
      <button onClick={toggleCamera} className="flip-camera-button">
        Flip Camera
      </button>
      
      {/* --- MODIFIED: Pass facingMode to CameraFeed --- */}
      <CameraFeed ref={videoRef} facingMode={facingMode} />
      
      <OverlayCanvas />

      {mode === 'walkthrough' && renderWalkthroughUI()}
    </div>
  );
}

export default CPRView;