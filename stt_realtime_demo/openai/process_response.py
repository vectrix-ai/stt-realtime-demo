import json
import base64
import numpy as np

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
            #print(data)
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
            pass

        elif data['type'] == 'conversation.item.input_audio_transcription.completed':
            #print("Input audio transcription completed")
            #print(data)
            pass

        elif data['type'] == 'conversation.item.input_audio_transcription.completed':
            '''
            Returned when input audio transcription is enabled and a transcription succeeds.
            '''
            #print("Input audio transcription completed")
            #print(data)
            pass

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
            pass

        elif data['type'] == 'response.function_call_arguments.done':
            '''
            Returned when the model-generated function call arguments are done streaming. 
            Also emitted when a Response is interrupted, incomplete, or cancelled.
            '''
            print("Response function call arguments done")
            print(data['arguments'])

        else:
            pass
