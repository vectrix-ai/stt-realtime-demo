import asyncio
import websockets
import time
import pyaudio
import subprocess
import threading
import os
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize a Langchain Groq LLchain (Model: Llama3-70b-8192)



async def text_chunker(chunks):
    """Split text into chunks, ensuring to not break sentences."""
    splitters = (".", ",", "?", "!", ";", ":", "—", "-", "(", ")", "[", "]", "}", " ")
    buffer = ""

    async for text in chunks:
        if buffer.endswith(splitters):
            yield buffer + " "
            buffer = text
        elif text.startswith(splitters):
            yield buffer + text[0] + " "
            buffer = text[1:]
        else:
            buffer += text

    if buffer:
        yield buffer + " "

async def chat_completion():
    """Retrieve text from Groq and yield it chunk by chunk."""
    logger.info(f"Sending query to Groq")
    llm = ChatGroq(
            model="llama3-70b-8192",
            temperature=0,
            timeout=None,
            max_retries=2,
    )

    input_messages = [
        ("system", "Je bent een assistent die in het Nederlands verhalen schrijft."),
        ("user", "Schrijf een kort verhaal over Antwerpen."),
    ]

    template = ChatPromptTemplate(input_messages)
    chain = template | llm | StrOutputParser()

    response = await chain.ainvoke({})

    # Yield the response in chunks
    chunk_size = 100  # Adjust this value as needed
    for i in range(0, len(response), chunk_size):
        # Let's wait for 1 second before yielding the next chunk
        #await asyncio.sleep(1)
        yield response[i:i+chunk_size]

async def client():
    uri = "ws://localhost:8765"
    logger.info(f"Connecting to WebSocket server: {uri}")

    async with websockets.connect(uri) as websocket:
        try:
            start_time = time.time()
            logger.info("Initializing audio playback")
            p = pyaudio.PyAudio()

            ffmpeg_process = subprocess.Popen(
                [
                    'ffmpeg', '-i', 'pipe:0',
                    '-f', 's16le',
                    '-acodec', 'pcm_s16le',
                    '-ar', '44100',
                    '-ac', '1',
                    'pipe:1'
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0
            )

            stream = p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=44100,
                            output=True,
                            frames_per_buffer=1024)

            def read_and_play():
                try:
                    while True:
                        data = ffmpeg_process.stdout.read(4096)
                        if not data:
                            break
                        stream.write(data)
                except Exception as e:
                    logger.error(f"Playback error: {e}")
                finally:
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    logger.info("Playback thread finished")

            playback_thread = threading.Thread(target=read_and_play)
            playback_thread.start()

            first_chunk_received = False
            audio_receiving_complete = False

            async def receive_audio():
                nonlocal first_chunk_received, audio_receiving_complete
                try:
                    while True:
                        try:
                            message = await websocket.recv()
                            if isinstance(message, bytes):
                                if not first_chunk_received:
                                    first_chunk_received = True
                                    time_taken = time.time() - start_time
                                    logger.info(f"First audio chunk received after {time_taken:.3f} seconds.")

                                ffmpeg_process.stdin.write(message)
                                logger.info("Received and processed audio chunk")
                            elif isinstance(message, str) and message == "END_OF_AUDIO":
                                logger.info("Received END_OF_AUDIO from server")
                                break
                            else:
                                logger.warning(f"Received unexpected message: {message}")
                        except websockets.exceptions.ConnectionClosed:
                            logger.info("Connection closed by the server.")
                            break
                finally:
                    audio_receiving_complete = True
                    ffmpeg_process.stdin.close()
                    logger.info("Closed ffmpeg stdin")

            receive_audio_task = asyncio.create_task(receive_audio())

            # Stream text chunks to the server
            async for text_chunk in text_chunker(chat_completion()):
                logger.info(f"Sending text chunk to server: {text_chunk}")
                await websocket.send(text_chunk)

            logger.info("Sending END_OF_TEXT to server")
            await websocket.send("END_OF_TEXT")

            # Wait for audio reception to complete
            await receive_audio_task

            # Wait for ffmpeg process to finish processing
            ffmpeg_process.wait()
            logger.info("ffmpeg process finished")

            # Wait for playback thread to finish
            playback_thread.join()
            logger.info("Audio playback completed")

        except Exception as e:
            logger.error(f"An error occurred: {e}")
        finally:
            if not websocket.closed:
                await websocket.close()
            logger.info("WebSocket connection closed")

# Run the client
asyncio.run(client())