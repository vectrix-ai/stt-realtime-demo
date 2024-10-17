import json
from stt_realtime_demo.maps.distance_matrix import calculate_distance_matrix


class Tools:
    def __init__(self, websocket):
        self.websocket = websocket

    def __send_response(self, call_id, name, arguments, output):
        """
        The client must respond to the function call before by sending a conversation.item.create message with type: "function_call_output"
        """
        self.websocket.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "status": "completed",
                    "name": name,
                    "call_id": call_id,
                    "arguments": arguments,
                    "output": output
                }
            }))


    def call(self, call_id, name, arguments):
        if name == "calculate_distance_matrix":
            origins = arguments['origins']
            destinations = arguments['destinations']
            mode = arguments.get('mode', 'driving')
            language = arguments.get('language', 'en')
            avoid = arguments.get('avoid', None)
            units = arguments.get('units', 'metric')
            departure_time = arguments.get('departure_time', None)
            response = calculate_distance_matrix(origins, destinations, mode, language, avoid, units, departure_time)
            self.__send_response(call_id=call_id, name=name, arguments=arguments, output=response)

        else:
            raise ValueError(f"Function {name} not found")

