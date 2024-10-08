import asyncio
import json
import os
import websockets
from dotenv import load_dotenv
import numpy as np
import sounddevice as sd
import base64

# Load environment variables from .env file
load_dotenv()

# Get the OpenAI API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")

url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

async def connect_to_openai():
    async with websockets.connect(
        url,
        extra_headers={
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1",
        }
    ) as websocket:
        print("Connected to server.")

        

        # Configure the session configuration
        await websocket.send(json.dumps({
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"] # Change this to ["text"] for text output only
            }
        }))

        # Send initial message
        await websocket.send(json.dumps({
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "instructions": "You are an AI assistant answering all the questions. ",
            }
        }))

        # Start audio stream
        stream = sd.InputStream(samplerate=24000, channels=1, dtype='int16')
        stream.start()

        # Initialize audio output stream
        output_stream = sd.OutputStream(samplerate=24000, channels=1, dtype='int16')
        output_stream.start()

        while True:
            # Read audio data
            audio_data, _ = stream.read(4800)  # 200ms chunks
            audio_base64 = base64.b64encode(audio_data.tobytes()).decode('utf-8')

            # Send audio data
            await websocket.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }))

            # Commit audio buffer and request response
            #await websocket.send(json.dumps({"type": "input_audio_buffer.commit"}))
            #await websocket.send(json.dumps({"type": "response.create"}))

            # Listen for messages
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                data = json.loads(message)

                if data['type'] == 'response.audio.delta':
                        audio_data = base64.b64decode(data['delta'])
                        audio_array = np.frombuffer(audio_data, dtype=np.int16)
                        output_stream.write(audio_array)
                else:
                    print(data)
            except asyncio.TimeoutError:
                pass

asyncio.run(connect_to_openai())