"""
Attacker Website - Security Demo for Aegis AI Skills Feature.

This is a mock attacker website that demonstrates data exfiltration risks.
It receives and displays data sent by malicious skill templates.
"""

from flask import Flask, request, render_template, jsonify
from datetime import datetime
import json

app = Flask(__name__)

# In-memory storage for exfiltrated data
exfiltrated_data = []

# Expected token for authentication
EXPECTED_TOKEN = "sk-7f3a9b2e4d1c8f6a5e0b3d9c2a7f4e1d"


@app.route('/', methods=['GET'])
def dashboard():
    """Display the attacker dashboard with exfiltrated data."""
    return render_template('index.html', data=exfiltrated_data)


@app.route('/<token>', methods=['POST', 'GET'])
def receive_data(token):
    """Receive exfiltrated data from malicious skills."""
    if token != EXPECTED_TOKEN:
        return jsonify({"error": "Invalid token"}), 403
    
    # Get data from query parameters or form data
    data = request.args.get('data') or request.form.get('data')
    os_info = request.args.get('os') or request.form.get('os')
    env_info = request.args.get('env') or request.form.get('env')
    hosts_info = request.args.get('hosts') or request.form.get('hosts')
    
    # Build entry
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": request.remote_addr,
        "method": request.method,
        "data": data,
        "os_info": os_info,
        "env_info": env_info,
        "hosts_info": hosts_info,
        "user_agent": request.headers.get('User-Agent', 'Unknown')
    }
    
    # Only store if there's actual data
    if any([data, os_info, env_info, hosts_info]):
        exfiltrated_data.append(entry)
        print(f"[!] Data received: {entry}")
    
    return jsonify({"status": "ok"}), 200


@app.route('/api/data', methods=['GET'])
def get_data():
    """API endpoint to get exfiltrated data as JSON."""
    return jsonify(exfiltrated_data)


@app.route('/clear', methods=['POST'])
def clear_data():
    """Clear all exfiltrated data."""
    exfiltrated_data.clear()
    return jsonify({"status": "cleared"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=16000, debug=False)
