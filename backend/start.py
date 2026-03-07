import subprocess
import sys

# This bypasses the console's "-m" issue by running it inside Python
if __name__ == "__main__":
    # 1. Install uvicorn just in case it's missing
    subprocess.run([sys.executable, "-m", "pip", "install", "uvicorn", "fastapi"])
    
    # 2. Start the server using the absolute path to uvicorn
    # We use a list to avoid shell parsing issues
    cmd = ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
    subprocess.run(cmd)