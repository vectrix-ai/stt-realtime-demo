import json
import base64
import asyncio

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