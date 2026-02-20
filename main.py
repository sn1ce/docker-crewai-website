import os
import re
import subprocess
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI()

CREWAI_DIR = os.getenv("CREWAI_DIR", "/crewai/website_builder")
CONFIG_DIR = os.path.join(CREWAI_DIR, "src/website_builder/config")
MAIN_PY = os.path.join(CREWAI_DIR, "src/website_builder/main.py")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/crewai/output")

running_process = None

class RunRequest(BaseModel):
    topic: str

class YamlPayload(BaseModel):
    content: str

def read_yaml(path):
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

def write_yaml(path, data):
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

@app.get("/api/agents")
def get_agents():
    return read_yaml(os.path.join(CONFIG_DIR, "agents.yaml"))

@app.post("/api/agents")
def save_agents(payload: YamlPayload):
    try:
        data = yaml.safe_load(payload.content)
        write_yaml(os.path.join(CONFIG_DIR, "agents.yaml"), data)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/api/tasks")
def get_tasks():
    return read_yaml(os.path.join(CONFIG_DIR, "tasks.yaml"))

@app.post("/api/tasks")
def save_tasks(payload: YamlPayload):
    try:
        data = yaml.safe_load(payload.content)
        write_yaml(os.path.join(CONFIG_DIR, "tasks.yaml"), data)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/api/topic")
def get_topic():
    try:
        with open(MAIN_PY) as f:
            content = f.read()
        match = re.search(r"'topic'\s*:\s*'([^']*)'", content)
        if match:
            return {"topic": match.group(1)}
        return {"topic": ""}
    except Exception:
        return {"topic": ""}

@app.post("/api/run")
def run_crew(req: RunRequest):
    global running_process
    if running_process and running_process.poll() is None:
        raise HTTPException(400, "Crew already running")
    try:
        with open(MAIN_PY) as f:
            content = f.read()
        content = re.sub(r"('topic'\s*:\s*)'[^']*'", f"\\1'{req.topic}'", content)
        with open(MAIN_PY, "w") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(500, f"Failed to update main.py: {e}")
    return {"ok": True}

@app.get("/api/logs")
def stream_logs():
    import sys
    def generate():
        global running_process
        venv_sp = "/crewai/website_builder/.venv/lib/python3.12/site-packages"
        project_src = os.path.join(CREWAI_DIR, "src")
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = "/crewai/website_builder/.venv"
        env["PYTHONPATH"] = f"{project_src}:{venv_sp}"
        # Run the crew entry point directly, bypassing 'crewai run' / uv
        running_process = subprocess.Popen(
            [sys.executable, "-c",
             "from website_builder.main import run; run()"],
            cwd=CREWAI_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        yield "data: [CREW STARTED]\n\n"
        try:
            for line in running_process.stdout:
                yield f"data: {line.rstrip()}\n\n"
            running_process.wait()
            yield f"data: [CREW FINISHED] exit code: {running_process.returncode}\n\n"
        except GeneratorExit:
            running_process.terminate()
    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.post("/api/stop")
def stop_crew():
    global running_process
    if running_process and running_process.poll() is None:
        running_process.terminate()
        return {"ok": True}
    return {"ok": False, "message": "No running crew"}

@app.get("/api/output")
def list_output():
    try:
        return {"files": os.listdir(OUTPUT_DIR)}
    except Exception:
        return {"files": []}

@app.get("/api/ping/{machine}")
def ping_machine(machine: str):
    endpoints = {
        "gaming": "http://10.0.0.88:11434",
        "nas": "http://10.0.0.4:11434",
        "mac": "http://10.0.1.162:11434"
    }
    url = endpoints.get(machine)
    if not url:
        raise HTTPException(404, "Unknown machine")
    try:
        import urllib.request
        urllib.request.urlopen(url, timeout=3)
        return {"online": True}
    except Exception:
        return {"online": False}

app.mount("/", StaticFiles(directory="/app/static", html=True), name="static")
