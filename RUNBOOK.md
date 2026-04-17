# Runbook — Auto Scraper Project

Purpose: a concise operational runbook for starting, debugging, and recovering the
Streamlit dashboard so you (or I) can pick up quickly before a demo. Put simple
instructions here so next time you can say a trigger phrase (see "Assistant
Triggers") and I will act.

**Quick Start (Recommended — Conda)**

- Create the environment from the included specification and run Streamlit:

```powershell
C:\Users\farou\anaconda3\Scripts\conda.exe env create -f environment.yml -n auto_scraper
conda activate auto_scraper
python -m streamlit run app.py --server.port=8502
```

- If `environment.yml` is missing, create an env and install from `requirements.txt`:

```powershell
C:\Users\farou\anaconda3\Scripts\conda.exe create -n auto_scraper python=3.11 -y
conda activate auto_scraper
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port=8502
```

**Alternative: recreate `venv` (may hit Windows Smart App Control blocks)**

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port=8502
```

If `venv` raises ImportError about a `.pyd` being blocked, skip to the
"Smart App Control / Code Integrity" section.

**Free port 8502 (if 'Port 8502 is not available')**

1. See who is using the port:

```powershell
netstat -aon | findstr :8502
# or (PowerShell native):
Get-NetTCPConnection -LocalPort 8502 | Select-Object LocalAddress,LocalPort,RemoteAddress,State,OwningProcess
```

2. Confirm PID and command:

```powershell
tasklist /FI "PID eq <PID>"
Get-CimInstance Win32_Process -Filter "ProcessId=<PID>" | Select-Object ProcessId,CommandLine
```

3. If it is a previous Streamlit/python you started, stop it:

```powershell
taskkill /PID <PID> /F
# or (PowerShell):
Stop-Process -Id <PID> -Force
```

**Smart App Control / Code Integrity (pandas .pyd blocked)**

Symptoms: ImportError: "DLL load failed while importing period: A Smart App Control or Code Integrity policy blocked this file." This is an OS-level security block of compiled Python extensions (example: `pandas\\_libs\\tslibs\\period.cp*.pyd`).

Safe actions:

1. Preferred: use Conda (see Quick Start). Conda's signed packages nearly always avoid this block on modern Windows systems.

2. If you must use `venv`, collect the Code Integrity events to see exact file paths (copyable):

```powershell
# Save recent Code Integrity events (repo root)
Get-WinEvent -LogName 'Microsoft-Windows-CodeIntegrity/Operational' -MaxEvents 200 | Select-Object TimeCreated, Id, Message | Format-List > code_integrity_events.txt

# Filter events mentioning pandas
Get-WinEvent -LogName 'Microsoft-Windows-CodeIntegrity/Operational' | Where-Object { $_.Message -like '*pandas*' } | Select-Object TimeCreated, Id, Message | Format-List > pandas_code_integrity.txt
```

3. Open Windows Security → App & browser control → Protection history. Locate the Code Integrity/Smart App Control event and use the "Allow on device" or similar option (requires admin). This is less safe and should be a last resort.

4. Alternative: run inside WSL/Linux or in a container (no Smart App Control there).

**Logs & Diagnostics**
- Streamlit server output appears in the terminal you used to run it; note the Local URL (http://localhost:8502).
- Use `prestart_check.py` to verify pandas/imports before launching (the repo includes this helper).
- You can save event log files (see above) and attach them if you want me to parse them.

**Assistant Triggers — exact phrases you can say next time**

When you say one of these exact phrases, I will perform the associated actions (ask for confirmation if the action will change system state):

-- "READ RUNBOOK AND START STREAMLIT (CONDA)" — create the conda env (if missing) and start Streamlit on port 8502.
- "READ RUNBOOK AND CREATE VENV" — create `./.venv`, install `requirements.txt`, and start Streamlit in the venv (warn about code integrity blocks).
-- "READ RUNBOOK AND FREE PORT 8502" — detect and stop processes holding port 8502 then start Streamlit (if requested).
- "READ RUNBOOK AND EXTRACT CI LOGS" — run the `Get-WinEvent` commands above and save `code_integrity_events.txt` in the repo root; then I will parse blocked file paths.

Use the exact phrase (caps not required) so I can match and run the steps automatically.

**Presentation Checklist**

- Use `run_streamlit_conda.ps1` before a demo (it automates env creation + launch). Test once locally.
- Confirm port 8502 is free. Start Streamlit and open http://localhost:8502 to verify UI.
- If CI blocks appear, prefer conda; if you must whitelist, escalate to admin and provide the `pandas_code_integrity.txt` file.

**Short notes / history**

- 2026-04-15: repository hardened; added `prestart_check.py`, conda helpers, and short changelog `15_04_26.md`.
- If you ask me to "read the runbook and start", I'll follow the Conda flow by default.

---

If you want any additions to this file (extra checks, custom ports, or a one-click PowerShell wrapper), tell me which items to add and I'll update it.

**Quick Commands — Copy / Paste (PowerShell)**

- Create a `logs/` folder and capture test outputs:

```powershell
mkdir logs
.\.venv\Scripts\python.exe scripts\test_session.py > logs/test_session.txt 2>&1
.\.venv\Scripts\python.exe scripts\test_predictor_io.py > logs/test_predictor_io.txt 2>&1
.\.venv\Scripts\python.exe scripts\test_model_manager.py > logs/test_model_manager.txt 2>&1
.\.venv\Scripts\python.exe diagnostic.py > logs/diagnostic.txt 2>&1
```

- Run Streamlit (use port 8502 to avoid conflicts) and save runtime log:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port=8502 > logs/streamlit.log 2>&1
```

- Health check (background health endpoint):

```powershell
Invoke-RestMethod http://127.0.0.1:8765/healthz
# or with curl:
curl http://127.0.0.1:8765/healthz
```

-- Quick way to free port 8502 (if required):

```powershell
netstat -aon | findstr :8502
tasklist /FI "PID eq <PID>"
taskkill /PID <PID> /F
```

These commands are useful for demos and for collecting logs if something goes wrong. If you want, I can re-run the smoke tests and write these log files into `logs/` now.
