from dotenv import load_dotenv
load_dotenv()

import os
import websockets
import json
import asyncio

from stt_realtime_demo.openai.process_response import receive_messages
from stt_realtime_demo.openai.send import send_audio_data

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
                "modalities": ["text", "audio"],
                "tools": [
                    {
                        "type": "function",
                        "name": "calculate_distance_matrix",
                        "description": "Calculate the driving distance and time between two locations using Google Maps.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "origins": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "description": "The starting point for the calculation (e.g., 'New York City, NY')."
                                    },
                                    "description": "A list of origin locations."
                                },
                                "destinations": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "description": "The destination point for the calculation (e.g., 'Chicago, IL')."
                                    },
                                    "description": "A list of destination locations."
                                },
                                "mode": {
                                    "type": "string",
                                    "enum": ["driving", "walking", "bicycling", "transit"],
                                    "default": "driving",
                                    "description": "The mode of transportation (default is 'driving')."
                                },
                                "avoid": {
                                    "type": "string",
                                    "enum": ["tolls", "ferries", "highways"],
                                    "default": "tolls",
                                    "description": "What routes to avoid during the calculation (default is 'tolls')."
                                },
                                "units": {
                                    "type": "string",
                                    "enum": ["metric", "imperial"],
                                    "default": "metric",
                                    "description": "Units for the results (default is 'metric')."
                                },
                                "departure_time": {
                                    "type": "string",
                                    "format": "date-time",
                                    "default": "now",
                                    "description": "The departure time for the calculation in ISO 8601 format (default is the current time)."
                                }
                            },
                            "required": ["origins", "destinations"]
                        }
                    }
                ]
            }
        }))
        # Send initial message (if needed)
        await websocket.send(json.dumps({
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "instructions": "You are an assistant from the company NDQ that helps drivers from trucks to plan and to estimate distances between two various locations.",
            }
        }))

        # Create tasks for sending and receiving
        send_task = asyncio.create_task(send_audio_data(websocket, audio_input_queue))
        receive_task = asyncio.create_task(receive_messages(websocket, audio_output_queue))

        await asyncio.gather(send_task, receive_task)