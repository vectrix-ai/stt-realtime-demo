import asyncio
import numpy as np
import sounddevice as sd
import threading
import queue
from connect import connect_to_openai

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

def start_stream():
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
    start_stream()