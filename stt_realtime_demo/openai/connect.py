from dotenv import load_dotenv
load_dotenv()

import os
import websockets
import json
import asyncio

from process_response import receive_messages
from send import send_audio_data

api_key = os.getenv("OPENAI_API_KEY")
url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"


async def connect_to_openai(audio_input_queue, audio_output_queue):
    async with websockets.connect(
        url,
        extra_headers={
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1",
        }
    ) as websocket:
        print("Connected to server.")

        # Configure the session
        await websocket.send(json.dumps({
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"]
            }
        }))

        # Send initial message (if needed)
        await websocket.send(json.dumps({
            "type": "response.create",
            "response": {
                "modalities": ["text"],
                "instructions": "Je bent een AI assistent die in het Nederlands praat.",
            }
        }))

        # Create tasks for sending and receiving
        send_task = asyncio.create_task(send_audio_data(websocket, audio_input_queue))
        receive_task = asyncio.create_task(receive_messages(websocket, audio_output_queue))

        await asyncio.gather(send_task, receive_task)