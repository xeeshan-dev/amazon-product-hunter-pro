"""
Run Streamlit app (simpler, no Redis needed)
"""
import sys
import os
import subprocess

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("🚀 Starting Amazon Hunter Pro (Streamlit UI)")
print("=" * 60)

# Run streamlit
subprocess.run([
    sys.executable, "-m", "streamlit", "run",
    "src/app_v2.py",
    "--server.port=8501",
    "--server.address=0.0.0.0"
])
