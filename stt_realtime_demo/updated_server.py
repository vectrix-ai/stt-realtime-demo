import asyncio
import websockets
import os
from dotenv import load_dotenv
import json
import base64
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load the API key from the .env file
load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

voice_id = 's7Z6uboUuE4Nd8Q2nye6'  # Replace with your actual voice ID
model_id = 'eleven_turbo_v2_5'  # Or any other model you prefer

async def elevenlabs_tts_stream(text_iterator, voice_id, model_id):
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id={model_id}&language_code=nl"
    logger.info(f"Connecting to ElevenLabs API: {uri}")

    async with websockets.connect(uri) as websocket:
        # Send initial configuration
        await websocket.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "use_speaker_boost": False},
            "generation_config": {
                "chunk_length_schedule": [120, 160, 250, 290]
            },
            "xi_api_key": ELEVENLABS_API_KEY,
        }))
        logger.info("Sent initial configuration to ElevenLabs API")

        # Start measuring time when the text is sent
        start_time = time.time()
        first_chunk_received = False

        async def listen():
            nonlocal first_chunk_received
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data.get("audio"):
                        if not first_chunk_received:
                            first_chunk_received = True
                            time_taken = time.time() - start_time
                            logger.info(f"First audio chunk received after {time_taken:.3f} seconds.")
                        logger.debug(f"Audio chunk received at {time.time():.3f} seconds.")
                        yield base64.b64decode(data["audio"])
                    elif data.get('isFinal'):
                        logger.info("Received final message from ElevenLabs API")
                        break
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("Connection closed unexpectedly")
                    break

        listen_task = asyncio.create_task(process_audio_chunks(listen()))

        for text in text_iterator:
            logger.info(f"Sending text to ElevenLabs API: {text[:50]}...")
            await websocket.send(json.dumps({"text": text}))

        logger.info("Sending empty text to signal end of input")
        await websocket.send(json.dumps({"text": ""}))

        async for chunk in listen_task:
            yield chunk

async def process_audio_chunks(audio_chunks):
    async for chunk in audio_chunks:
        yield chunk

async def handler(websocket, path):
    logger.info("New client connected")
    buffer = ""
    async for message in websocket:
        logger.info(f"Received message from client: {message}")
        if message == "END_OF_TEXT":
            logger.info("Received END_OF_TEXT from client")
            break
        buffer += message
        if buffer.endswith((".", "!", "?", "\n")):
            logger.info(f"Processing buffer: {buffer}")
            async for audio_chunk in elevenlabs_tts_stream([buffer], voice_id, model_id):
                logger.debug(f"Sending audio chunk to client at {time.time():.3f} seconds.")
                await websocket.send(audio_chunk)
            buffer = ""

    if buffer:
        logger.info(f"Processing remaining buffer: {buffer}")
        async for audio_chunk in elevenlabs_tts_stream([buffer], voice_id, model_id):
            logger.debug(f"Sending audio chunk to client at {time.time():.3f} seconds.")
            await websocket.send(audio_chunk)

    logger.info("Sending END_OF_AUDIO to client")
    await websocket.send("END_OF_AUDIO")
    logger.info("Client disconnected")

# Start the WebSocket server
start_server = websockets.serve(handler, "0.0.0.0", 8765)

logger.info("Starting WebSocket server on 0.0.0.0:8765")
asyncio.get_event_loop().run_until_complete(start_server)
logger.info("WebSocket server is running. Press Ctrl+C to stop.")
asyncio.get_event_loop().run_forever()