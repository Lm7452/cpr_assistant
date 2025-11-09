import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
from app.cpr_analyzer import CPRAnalyzer # Import our new class

# Initialize the FastAPI app
app = FastAPI()

# Create a single analyzer instance to be shared
# This way, it retains the BPM history for all connections
# Note: This is a simple approach; for multiple users, we'd manage this differently
analyzer = CPRAnalyzer()

@app.websocket("/ws/cpr")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected!")
    
    try:
        while True:
            # Receive the JSON message from the client
            data = await websocket.receive_text()
            
            # The client sends JSON: {"image": "base64...", "show_hands": true/false, "blur_face": true/false, "show_face": true/false}
            message_data = json.loads(data)
            image_data_url = message_data.get("image")
            show_hands = message_data.get("show_hands", False)  # Default to False
            blur_face = message_data.get("blur_face", True)  # Default to True (always blur in non-dev)
            show_face = message_data.get("show_face", False)  # Default to False (never show unblurred in non-dev)
            
            if not image_data_url:
                continue

            # Process the frame using our analyzer
            feedback = analyzer.process_frame(image_data_url, show_hands=show_hands, blur_face=blur_face, show_face=show_face)
            
            # --- [THE FIX] ---
            # Remove "if feedback:" and just send the result.
            # This guarantees the frontend gets an update on every frame.
            await websocket.send_json(feedback)
            # --- [END OF FIX] ---

    except WebSocketDisconnect:
        print("Client disconnected")
        # Reset analyzer state for the next connection (in this simple setup)
        analyzer.__init__() 
    except Exception as e:
        print(f"An error occurred: {e}")
        await websocket.close(code=1011)