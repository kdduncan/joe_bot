import logging
import sys
from database import SQLJobDatabase
from agent_orchestrator import AgentOrchestrator
from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO)

print("--- Initializing DB ---")
db = SQLJobDatabase()

print("--- Initializing Orchestrator ---")
try:
    orch = AgentOrchestrator(db)
    print(f"Orchestrator Enabled: {orch.enabled}")
    
    if orch.enabled:
        print("--- Running Test Query ---")
        result = orch.process_query("How many jobs in Iowa in 2024?")
        print("--- Result ---")
        print(result)
    else:
        print("Orchestrator DISABLED (Check API Key)")

except Exception as e:
    print(f"\n❌ CRASH: {e}")
    import traceback
    traceback.print_exc()
