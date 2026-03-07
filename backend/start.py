import subprocess
import sys
import os

if __name__ == "__main__":
    # 1. Install EVERYTHING from your requirements file
    print("Installing requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # 2. Add current directory to path just in case
    os.environ["PYTHONPATH"] = os.getcwd()

    # 3. Start the server
    print("Starting Uvicorn...")
    cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
    subprocess.run(cmd)