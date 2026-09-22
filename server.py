import os
import base64
import time
import shutil
import psutil
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
from google.genai import types

app = Flask(__name__, static_folder='.')
CORS(app)

API_KEY = "AQ.Ab8RN6JJ20mj_mq2y6X7Xwsg9YuXSHkDl38tn8OAXbMXWMVzTg"
client = genai.Client(api_key=API_KEY)

def get_system_health_metrics():
    """Gathers CPU, Memory, Disk, and detailed Battery telemetry."""
    cpu_percent = psutil.cpu_percent(interval=0.4)
    cpu_cores = psutil.cpu_count(logical=True)
    
    mem = psutil.virtual_memory()
    ram_total = round(mem.total / (1024 ** 3), 2)
    ram_used = round(mem.used / (1024 ** 3), 2)
    
    disk = psutil.disk_usage('/')
    disk_total = round(disk.total / (1024 ** 3), 2)
    disk_free = round(disk.free / (1024 ** 3), 2)
    
    battery_details = "Not available (Desktop/AC Plugged)"
    power_plugged = True
    if hasattr(psutil, "sensors_battery"):
        bat = psutil.sensors_battery()
        if bat:
            power_plugged = bat.power_plugged
            status_text = "Charging / Plugged In" if bat.power_plugged else "Discharging (Battery)"
            time_left = f"{round(bat.secsleft / 60)} mins" if bat.secsleft > 0 else "Calculating"
            battery_details = f"{bat.percent}% ({status_text}, Est. Time: {time_left})"

    return f"""
[HARDWARE & POWER TELEMETRY]
- CPU Load: {cpu_percent}% across {cpu_cores} Logical Cores
- RAM: {ram_used} GB / {ram_total} GB ({mem.percent}%)
- Storage Disk (C:): {disk_free} GB free out of {disk_total} GB ({disk.percent}% used)
- Battery & Power Status: {battery_details}
- Power Source: {"AC Adapter" if power_plugged else "Battery Power"}
"""

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    data = request.get_json(force=True)
    user_query = data.get("message", "").strip()
    file_data = data.get("file_base64", None)
    mime_type = data.get("mime_type", None)

    if not user_query and not file_data:
        return jsonify({"reply": "Please enter a prompt, select a tool, or attach a file."})

    contents = []
    if file_data and mime_type:
        file_bytes = base64.b64decode(file_data)
        contents.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))

    q_lower = user_query.lower()

    # 1. System Health & Power Monitor Trigger
    if any(k in q_lower for k in ["system health", "system stats", "power system", "battery health", "power monitor", "hardware status"]):
        telemetry = get_system_health_metrics()
        prompt = f"""User requested System Health & Power Diagnostic.
{telemetry}
User Query: {user_query}

Task:
1. Provide a Markdown table showing CPU, RAM, Disk, and Battery Metrics.
2. Provide a Power & Thermal Optimization Verdict.
3. List 3 actionable steps to extend battery life or optimize performance.
If the query is in Telugu, reply in Telugu."""
        contents.append(prompt)

    # 2. Log & Error Debugger Trigger
    elif any(k in q_lower for k in ["error", "exception", "traceback", "fatal", "log", "debug", "failed"]) or "Traceback (most recent call last):" in user_query:
        prompt = f"""Analyze this software/system error log:
{user_query}

Task:
1. Error Summary: Root cause identification.
2. Severity Rating: Low / Medium / Critical.
3. Step-by-step fix: Exact code snippets or command-line solutions.
If the query is in Telugu, reply in Telugu."""
        contents.append(prompt)

    # 3. Linux & Terminal Helper Trigger
    elif any(k in q_lower for k in ["linux", "bash", "terminal", "shell", "ubuntu", "command"]):
        prompt = f"""The user needs Linux/Terminal command assistance:
User Query: {user_query}

Task:
Provide exact terminal commands with clear flags, syntax explanations, and safety warnings (e.g. for sudo/rm operations).
If the query is in Telugu, reply in Telugu."""
        contents.append(prompt)

    # 4. Academic & Multimodal Helper
    else:
        if user_query:
            contents.append(user_query)
        else:
            contents.append("Please analyze the attached image/document thoroughly.")

    active_model = 'gemini-2.5-flash'

    err_msg = "Unknown error"
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=active_model,
                contents=contents,
                config={
                    "system_instruction": (
                        "You are an All-in-One AI System Assistant. You support academic guidance, "
                        "hardware diagnostics, log debugging, and Linux systems administration. "
                        "Always format responses with Markdown headers, bullet points, and code blocks."
                    )
                }
            )
            if response and response.text:
                return jsonify({"reply": response.text})
        except Exception as e:
            err_msg = str(e)
            print(f"[Error]: {err_msg}")
            time.sleep(1)

    return jsonify({"reply": f"API Error: {err_msg}"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"\nAI Backend Running on port {port}...\n")
    app.run(host='0.0.0.0', port=port, debug=False)
