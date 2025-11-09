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
  
  const [annotatedFrame, setAnnotatedFrame] = useState(null);

  const onSocketMessage = useCallback((data) => {
    setFeedback(data);
    if (data.annotated_frame) {
      setAnnotatedFrame(data.annotated_frame);
    }
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
      <div style={{ position: 'relative', display: 'inline-block' }}>
        <CameraFeed ref={videoRef} facingMode={facingMode} />
        {annotatedFrame && (
          <img
            src={annotatedFrame}
            alt="Annotated frame with MediaPipe landmarks"
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              pointerEvents: 'none',
              zIndex: 1
            }}
          />
        )}
      </div>
      
      <OverlayCanvas />

      {mode === 'walkthrough' && renderWalkthroughUI()}
    </div>
  );
}

export default CPRView;