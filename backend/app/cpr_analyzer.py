import mediapipe as mp
import cv2
import numpy as np
import time
import base64
import re

class CPRAnalyzer:
    def __init__(self):
        # Initialize MediaPipe Pose
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1, # Use a simpler model for speed
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Initialize MediaPipe drawing utilities
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # --- Existing Variables ---
        self.compression_times = []
        self.compression_count = 0
        self.current_bpm = 0
        self.previous_bpm = 0
        self.message = "Begin compressions"
        
        # --- UPDATED STATE VARIABLES ---
        self.compression_state = "up" # Start in the "up" state
        # Set a 5% screen height threshold
        self.depth_threshold = 0.05 
        # This will now track the "peak" (highest or lowest point)
        self.peak_y = 0.5

    def decode_image(self, image_data_url: str):
        """Decodes a base64-encoded image from the frontend."""
        try:
            # Remove the 'data:image/jpeg;base64,' prefix
            img_data = re.sub('^data:image/.+;base64,', '', image_data_url)
            # Decode base64
            img_bytes = base64.b64decode(img_data)
            # Convert to numpy array
            np_arr = np.frombuffer(img_bytes, np.uint8)
            # Decode image
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            print(f"Error decoding image: {e}")
            return None

    def encode_image(self, frame):
        """Encodes a frame to base64 JPEG."""
        try:
            # Encode frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            # Convert to base64
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/jpeg;base64,{img_base64}"
        except Exception as e:
            print(f"Error encoding image: {e}")
            return None

    def calculate_bpm(self):
        """Calculate BPM using last 4 beats for better accuracy."""
        if len(self.compression_times) < 2:
            return 0
        
        # Use last 4 compressions (or as many as available)
        recent_times = self.compression_times[-4:]
        if len(recent_times) < 2:
            return 0

        # Calculate intervals
        intervals = [recent_times[i] - recent_times[i-1] for i in range(1, len(recent_times))]
        if not intervals:
            return 0
        
        avg_interval = sum(intervals) / len(intervals)
        bpm = 60 / avg_interval if avg_interval > 0 else 0
        
        # Smooth the BPM calculation (from your cpr_assistant.py)
        bpm = 0.7 * bpm + 0.3 * self.previous_bpm
        self.previous_bpm = bpm
        
        # Clamp between 0-200 BPM
        return min(max(bpm, 0), 200)

    def get_feedback_message(self, bpm):
        """Get feedback message based on BPM."""
        if bpm == 0 and self.compression_count == 0:
            return "Begin compressions"
        elif 100 <= bpm <= 120:
            return "Good rhythm!"
        elif bpm < 100 and bpm > 0:
            return "Too slow - speed up!"
        elif bpm > 120:
            return "Too fast - slow down!"
        return self.message # Keep the last message if BPM is 0 mid-compression

    def update_cpr_state(self, pose_landmarks):
        """
        Updates the compression state and counts compressions based on hand movement.
        This is the new, corrected state machine logic.
        """
        if not pose_landmarks:
            self.message = "Position your full body in view"
            return

        # Get Y-coordinate of wrists
        left_wrist = pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist = pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_WRIST]

        if left_wrist.visibility < 0.6 and right_wrist.visibility < 0.6:
            self.message = "Cannot see hands"
            return
            
        # Get the average vertical position of the hands (0.0 is top, 1.0 is bottom)
        current_y = (left_wrist.y + right_wrist.y) / 2

        # --- [NEW FIX] ---
        # Add a guard to ignore bad/unrealistic Y-values from MediaPipe
        if not 0.0 < current_y < 1.0:
            print(f"Bad Y value: {current_y:.2f}. Skipping frame.")
            self.message = "Positioning..."
            return
        # --- End of Fix ---

        # --- [DEBUG] Print the current Y value to your backend terminal ---
        print(f"State: {self.compression_state}, Current Y: {current_y:.2f}, Peak Y: {self.peak_y:.2f}")

        # --- Corrected State Machine Logic ---
        
        # STATE: "up" (Waiting for a downward push)
        if self.compression_state == "up":
            if current_y > self.peak_y + self.depth_threshold:
                # --- PUSHED DOWN ---
                self.compression_state = "down"
                self.peak_y = current_y
            elif current_y < self.peak_y:
                self.peak_y = current_y
        
        # STATE: "down" (Waiting for an upward release)
        elif self.compression_state == "down":
            if current_y < self.peak_y - self.depth_threshold:
                # --- RECOILED UP ---
                self.compression_state = "up"
                self.peak_y = current_y
                
                # --- A COMPLETE COMPRESSION IS COUNTED ---
                self.compression_count = (self.compression_count % 30) + 1
                
                current_time = time.time()
                self.compression_times.append(current_time)
                if len(self.compression_times) > 10:
                    self.compression_times.pop(0) # Keep the list short
            
            elif current_y > self.peak_y:
                self.peak_y = current_y

        # --- End of State Machine ---

        # Update BPM and message
        self.current_bpm = self.calculate_bpm()
        self.message = self.get_feedback_message(self.current_bpm)
        
        # Add recoil feedback
        if self.compression_state == "down" and "Good rhythm" in self.message:
            self.message = "Good rhythm! (Recoil)"

    def process_frame(self, image_data_url: str):
        """Main processing function."""
        frame = self.decode_image(image_data_url)
        annotated_frame = None
        
        # --- [THE FIX] ---
        # If the frame is bad, don't return None.
        # Instead, update the message and proceed to return the last known state.
        if frame is None:
            self.message = "Waiting for video..."
        else:
            # If the frame is good, run all the processing
            
            # Flip the frame to match the mirrored frontend view
            frame = cv2.flip(frame, 1)
            
            # Convert to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame with Pose
            pose_results = self.pose.process(rgb_frame)
            
            # Process the frame with Hands
            hands_results = self.hands.process(rgb_frame)
            
            # Create annotated frame
            annotated_frame = rgb_frame.copy()
            
            # Draw pose landmarks on the RGB frame
            if pose_results.pose_landmarks:
                self.mp_drawing.draw_landmarks(
                    annotated_frame,
                    pose_results.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS
                )
            
            # Draw hand landmarks on the RGB frame
            if hands_results.multi_hand_landmarks:
                for hand_landmarks in hands_results.multi_hand_landmarks:
                    self.mp_drawing.draw_landmarks(
                        annotated_frame,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS,
                        self.mp_drawing_styles.get_default_hand_landmarks_style(),
                        self.mp_drawing_styles.get_default_hand_connections_style()
                    )
            
            # Convert back to BGR for encoding
            annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR)
            
            if pose_results.pose_landmarks:
                # If we find a person, call our state function
                self.update_cpr_state(pose_results.pose_landmarks)
            else:
                # If no landmarks are found, update the message
                self.message = "Position body in frame"
        # --- [END OF FIX] ---

        # Encode annotated frame if available
        annotated_image_data = None
        if annotated_frame is not None:
            annotated_image_data = self.encode_image(annotated_frame)
        elif frame is not None:
            # If we have a frame but no annotations, still send it
            annotated_image_data = self.encode_image(frame)

        # This return now happens every time, even if the frame was bad,
        # ensuring the frontend always gets an update.
        result = {
            "bpm": int(self.current_bpm),
            "count": self.compression_count,
            "message": self.message
        }
        
        # Add annotated frame if available
        if annotated_image_data:
            result["annotated_frame"] = annotated_image_data
            
        return result