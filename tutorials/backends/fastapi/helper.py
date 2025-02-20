import subprocess
import os
import warnings

class FastAPIServer:
    """
    A class to manage the lifecycle of a FastAPI server.
    """

    def __init__(self, port, venv_path="fastapi-env", app_module="main:app"):
        """
        Initializes the FastAPI server manager.

        Parameters:
        port (int): The port to run the FastAPI server on.
        venv_path (str): Path to the virtual environment. Default is 'fastapi-env'.
        app_module (str): The FastAPI app module (e.g., 'main:app').
        """
        self.port = port
        self.venv_path = venv_path
        self.app_module = app_module
        self.process = None

    def run(self):
        """
        Starts the FastAPI server in a subprocess.
        """
        if self.process is not None:
            print("FastAPI server is already running.")
            return

        # Command to activate the virtual environment and run the FastAPI server
        command = (
            f"source {self.venv_path}/bin/activate && uvicorn {self.app_module} --reload --port {self.port} --timeout-keep-alive 600"
        )
        
        # Start the server process
        self.process = subprocess.Popen(
            command, shell=True, executable="/bin/bash", preexec_fn=os.setsid
        )
        print(f"FastAPI server started on port {self.port}.")
        print("Use .stop() method to kill the server.")

    def stop(self):
        """
        Stops the FastAPI server subprocess.
        """
        if self.process is None:
            print("FastAPI server is not running.")
            return

        try:
            # Kill the process group
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process = None
            print("FastAPI server stopped.")
        except Exception as e:
            print(f"Error stopping FastAPI server: {e}")

def run_fastapi(port):
    """
    This function runs the FastAPI server in a subprocess.

    Parameters:
    port (int): The port to run the FastAPI server on.

    Returns:
    subprocess.Popen: The FastAPI process
    """   
    msg = "This function will be deprecated on the next push. Please use the FastAPIServer class from the helper.py file."
    # Command to activate the virtual environment and run the FastAPI server
    command = f"source fastapi-env/bin/activate && uvicorn main:app --reload --port {port}"
    
    # Run the command in the shell with Popen
    fastapi_process = subprocess.Popen(command, shell=True, executable="/bin/bash", preexec_fn=os.setsid)

    return fastapi_process


def clean_tutorial():
    """
    This function cleans up the artifacts created during the tutorial.
    """
    # Activate the environment, uninstall the kernel, list kernels, and remove main.py
    commands = [
        "rm -f main.py"
    ]
    
    for command in commands:
        process = subprocess.run(command, shell=True, capture_output=True, text=True)
        print(f"Command: {command}")
        print(f"Return Code: {process.returncode}")
        if process.stdout:
            print(f"Output:\n{process.stdout}")
        if process.stderr:
            print(f"Error:\n{process.stderr}")
        print("-" * 40)


def kernel_validation():
    """
    This function validates that the notebook is running in the correct environment.
    """
    user_input = input("Is the notebook running in `SilverAIWolf (FastAPI)? Type `yes` to continue: ")

    if user_input.lower() != "yes":
        msg = "The notebook must be running with `SilverAIWolf (FastAPI)` environment."
        raise Exception(msg)
        
    