import websockets
import asyncio
import papermill as pm
import os
import argparse
import json
import sys

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('ip', help='The listening ip')
parser.add_argument('port', help='The listening ip')
args = parser.parse_args()

PORT = args.port
server = args.ip


print("\nListeing on: ws://%s:%s" % (server, PORT))
print("Server app home directory: %s" % os.getcwd())


async def echo(websocket, path):
    print("A client just connected")    
    try:
        async for message in websocket:
            print("Received messaged from client: " + message)

            # extracting parameters
            parameter_dict = json.loads(message)
            notebook_path = parameter_dict.get("notebook_path")
            kernel_name = parameter_dict.get("kernel_name")
            notebook_parameters = parameter_dict.get("notebook_parameters")
            
            notebook_exist = os.path.exists(notebook_path)
            print("\nNotebook directory exist: %s" % notebook_exist)
            
            try:
                # running the notebook using papermill
                pm.execute_notebook(
                    notebook_path,
                    notebook_path,
                    kernel_name=kernel_name,
                    parameters=notebook_parameters)

                await websocket.send("Papermill ran the process: " + message)
            except Exception as e:
                print("{}".format(e))
    except websockets.exceptions.ConnectionClosed as e:
        print("A client just disconnected!")

start_server = websockets.serve(echo, server, PORT)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
