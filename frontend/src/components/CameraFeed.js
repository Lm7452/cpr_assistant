import React, { useEffect, forwardRef } from 'react';

const CameraFeed = forwardRef(({ facingMode }, ref) => {
  useEffect(() => {
    // Function to stop the current video stream
    const stopStream = () => {
      if (ref.current && ref.current.srcObject) {
        ref.current.srcObject.getTracks().forEach(track => track.stop());
      }
    };

    // Function to get camera access
    const getCamera = async () => {
      if (!ref.current) {
        return;
      }
      
      // Stop any existing stream before getting a new one
      stopStream();

      try {
        // --- MODIFIED: Use the facingMode prop ---
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            facingMode: facingMode // Use the prop here
          }
        });
        
        ref.current.srcObject = stream;
        
        ref.current.play().catch(err => {
          console.error("Error playing video:", err);
        });
        
      } catch (err) {
        console.error("Error accessing camera:", err);
        alert("Could not access camera. Please check permissions.");
      }
    };

    getCamera();

    // Cleanup: stop the stream when the component unmounts
    return () => {
      stopStream();
    };
    
  // --- MODIFIED: Re-run this effect if facingMode changes ---
  }, [ref, facingMode]); 

  return (
    <video
      ref={ref}
      className="camera-feed"
      autoPlay
      playsInline
      muted
      // We flip the video based on which camera is active
      style={{ transform: facingMode === 'user' ? 'rotateY(180deg)' : 'none' }}
    />
  );
});

export default CameraFeed;