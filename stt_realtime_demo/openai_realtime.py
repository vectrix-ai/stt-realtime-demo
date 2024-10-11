import asyncio
import json
import os
import websockets
from dotenv import load_dotenv
import numpy as np
import sounddevice as sd
import base64
import threading
import queue
from elevenlabs.client import AsyncElevenLabs
import httpx
from elevenlabs import stream




# Load environment variables from .env file
load_dotenv()

# Load the Elenlabs client
client = AsyncElevenLabs(
  api_key=os.getenv("ELEVENLABS_API_KEY"),  # Defaults to ELEVEN_API_KEY
  httpx_client=httpx.AsyncClient()
)



# Get the OpenAI API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")
url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

def audio_input_thread(audio_input_queue):
    with sd.InputStream(samplerate=24000, channels=1, dtype='int16') as stream:
        while True:
            audio_data, _ = stream.read(4800)
            audio_input_queue.put(audio_data.copy())

def audio_output_thread(audio_output_queue):
    with sd.OutputStream(samplerate=24000, channels=1, dtype='int16') as stream:
        while True:
            try:
                audio_data = audio_output_queue.get(timeout=0.1)
                stream.write(audio_data)
            except queue.Empty:
                # Output silence if no data is available
                stream.write(np.zeros((4800, 1), dtype='int16'))

async def send_audio_data(websocket, audio_input_queue):
    while True:
        # Get audio data from the queue
        audio_data = await asyncio.get_event_loop().run_in_executor(None, audio_input_queue.get)
        
        # Convert audio data to bytes
        audio_bytes = audio_data.tobytes()
        
        # Ensure the audio data is in little-endian format
        if audio_data.dtype.byteorder == '>':
            # Big-endian, convert to little-endian
            audio_data = audio_data.byteswap().newbyteorder()
            audio_bytes = audio_data.tobytes()
        
        # Encode to base64 string
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        # Construct the message as per the OpenAI API specification
        event = {
            "type": "input_audio_buffer.append", 
            "audio": audio_base64}
        # Send the message
        await websocket.send(json.dumps(event))

async def receive_messages(websocket, audio_output_queue):
    while True:
        message = await websocket.recv()
        data = json.loads(message)
        if data['type'] == 'response.audio.delta':
            audio_data = base64.b64decode(data['delta'])
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            audio_output_queue.put(audio_array.reshape(-1, 1))
        elif data['type'] == 'response.final':
            # Handle the final response if needed
            pass

        elif data['type'] == 'session.updated':
            '''
            This is sent when the session is updated, for example when the model changes.
            '''
            print("Session updated")
            print(data)

        elif data['type'] == 'conversation.item.created':
            #print("Conversation item created")
            print(data)
            pass

        elif data['type'] == 'response.audio_transcript.delta':
            '''
            This is sent when the model is generating a response.
            '''
            # Prints the audio transcript of the response by the model
            #print("Response audio transcript delta")
            #print(data)
            pass

        elif data['type'] == 'session.created':
            print("Session created")
            #print(data)

        elif data['type'] == 'conversation.item.input_audio_transcription.completed':
            print("Input audio transcription completed")
            #print(data)

        elif data['type'] == 'conversation.item.input_audio_transcription.completed':
            '''
            Returned when input audio transcription is enabled and a transcription succeeds.
            '''
            print("Input audio transcription completed")
            print(data)

        elif data['type'] == 'response.content_part.added':
            '''
            Returned when a new content part is added to an assistant message item during response generation.
            '''
            #print("Response content part added")
            #print(data)
            pass

        elif data['type'] == 'response.text.delta':
            '''
            Returned when the text value of a "text" content part is updated.
            '''
            #print("Response text delta")
            #print(data)
            pass
        elif data['type'] == 'response.text.done':
            '''
            Returned when the text value of a "text" content part is done streaming. Also emitted when a Response is interrupted, incomplete, or cancelled.
            '''
            print("Response text done")
            print(data['text'])
            #audio_stream = await client.stream(text=data['text'])
            #stream(audio_stream)


        else:
            pass

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
                "modalities": ["text"]
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

def main():
    # Create queues
    audio_input_queue = queue.Queue()
    audio_output_queue = queue.Queue()
    
    # Start audio threads
    input_thread = threading.Thread(target=audio_input_thread, args=(audio_input_queue,))
    input_thread.daemon = True
    input_thread.start()
    
    output_thread = threading.Thread(target=audio_output_thread, args=(audio_output_queue,))
    output_thread.daemon = True
    output_thread.start()
    
    # Run the asyncio code
    asyncio.run(connect_to_openai(audio_input_queue, audio_output_queue))

if __name__ == "__main__":
    main()