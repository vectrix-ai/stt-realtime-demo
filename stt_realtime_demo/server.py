import asyncio
import websockets
import os
from dotenv import load_dotenv
import json
import base64
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load the API key from the .env file
load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

voice_id = 's7Z6uboUuE4Nd8Q2nye6'  # Replace with your actual voice ID
model_id = 'eleven_turbo_v2_5'  # Or any other model you prefer
async def elevenlabs_tts_stream(websocket):
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id={model_id}&language_code=nl"

    logger.info(f"Connecting to ElevenLabs API: {uri}")
    async with websockets.connect(uri) as elevenlabs_ws:
        # Send initial configuration
        await elevenlabs_ws.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "use_speaker_boost": False},
            "generation_config": {
                "chunk_length_schedule": [120, 160, 250, 290]
            },
            "xi_api_key": ELEVENLABS_API_KEY,
        }))
        logger.info("Sent initial configuration to ElevenLabs API")

        # Start a task to receive audio from ElevenLabs and send it to the client
        async def receive_and_send_audio():
            try:
                while True:
                    message = await elevenlabs_ws.recv()
                    data = json.loads(message)
                    if data.get("audio"):
                        audio_chunk = base64.b64decode(data["audio"])
                        await websocket.send(audio_chunk)
                        logger.info("Sent audio chunk to client")
                    elif data.get('isFinal'):
                        logger.info("Received final message from ElevenLabs API")
                        await websocket.send("END_OF_AUDIO")
                        break
            except websockets.exceptions.ConnectionClosed:
                logger.info("Connection to ElevenLabs API closed")
                await websocket.send("END_OF_AUDIO")

        audio_task = asyncio.create_task(receive_and_send_audio())

        # Receive text chunks from the client and send them to ElevenLabs
        try:
            while True:
                message = await websocket.recv()
                if message == "END_OF_TEXT":
                    logger.info("Received END_OF_TEXT from client")
                    await elevenlabs_ws.send(json.dumps({"text": ""}))
                    break
                logger.info(f"Received text chunk from client: {message}")
                await elevenlabs_ws.send(json.dumps({"text": message}))
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by the client")

        # Wait for the audio streaming to complete
        await audio_task

async def handler(websocket, path):
    logger.info("New client connected")
    await elevenlabs_tts_stream(websocket)
    logger.info("Client disconnected")

# Start the WebSocket server
start_server = websockets.serve(handler, "0.0.0.0", 8765)

logger.info("Starting WebSocket server on 0.0.0.0:8765")
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()