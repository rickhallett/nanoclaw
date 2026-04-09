#!/usr/bin/env python3
"""Day 8: subprocess — real SRE patterns.

Run: uv run python data/advisors/guido/curriculum/scripts/day08_subprocess_patterns.py
"""
from IPython import embed
import subprocess
import json

# ============================================================================
# PATTERN 1: Capture JSON output from CLI tools
# ============================================================================

print("=" * 60)
print("CHECKPOINT 1: JSON output parsing")
print("=" * 60)
print()
print("Many CLI tools output JSON: kubectl, docker, aws, gcloud, az.")
print("Pattern: run → capture → json.loads → use the data.")
print()
print("TRY (simulating kubectl output):")
print()
print("  # Simulate: kubectl get pods -o json")
print("  r = subprocess.run(")
print("      ['python3', '-c', '''")
print("  import json")
print("  print(json.dumps({")
print("      \"items\": [")
print("          {\"name\": \"web-01\", \"status\": \"Running\", \"restarts\": 0},")
print("          {\"name\": \"db-01\", \"status\": \"Pending\", \"restarts\": 0},")
print("          {\"name\": \"cache-01\", \"status\": \"CrashLoopBackOff\", \"restarts\": 5},")
print("      ]")
print("  }))'''],")
print("      capture_output=True, text=True, check=True")
print("  )")
print()
print("  data = json.loads(r.stdout)")
print("  for pod in data['items']:")
print("      print(f\"{pod['name']}: {pod['status']}\")")
print()
print("In production, the command would be:")
print("  ['kubectl', 'get', 'pods', '-n', 'halo-fleet', '-o', 'json']")
print()

# Pre-build the simulated output for use in the checkpoint
sim_kubectl = subprocess.run(
    ['python3', '-c', '''
import json
print(json.dumps({
    "items": [
        {"name": "web-01", "status": "Running", "restarts": 0, "cpu": "50m", "memory": "128Mi"},
        {"name": "db-01", "status": "Pending", "restarts": 0, "cpu": "100m", "memory": "256Mi"},
        {"name": "cache-01", "status": "CrashLoopBackOff", "restarts": 5, "cpu": "25m", "memory": "64Mi"},
        {"name": "worker-01", "status": "Running", "restarts": 1, "cpu": "200m", "memory": "512Mi"},
        {"name": "worker-02", "status": "OOMKilled", "restarts": 3, "cpu": "200m", "memory": "512Mi"},
    ]
}))'''],
    capture_output=True, text=True, check=True
)
kubectl_data = json.loads(sim_kubectl.stdout)

print("'kubectl_data' is loaded with simulated pod data.")
print("Explore it: kubectl_data['items'], etc.")

embed(header="Checkpoint 1: parse JSON output — kubectl_data is ready")

# ============================================================================
# PATTERN 2: Piping without shell=True
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: Piping in Python (no shell=True)")
print("=" * 60)
print()
print("Shell pipes: ps aux | grep python | wc -l")
print("In Python, do each step separately.")
print()
print("TRY:")
print("  # Step 1: get process list")
print("  ps = subprocess.run(['ps', 'aux'], capture_output=True, text=True)")
print()
print("  # Step 2: filter in Python (better than grep — you have full string methods)")
print("  python_procs = [l for l in ps.stdout.split('\\n') if 'python' in l.lower()]")
print("  print(f'Python processes: {len(python_procs)}')")
print("  for p in python_procs[:3]:")
print("      print(f'  {p[:80]}')")
print()
print("  # Step 3: you can also pipe output of one command to another")
print("  ps_out = subprocess.run(['ps', 'aux'], capture_output=True, text=True)")
print("  grep_out = subprocess.run(['grep', 'python'], input=ps_out.stdout,")
print("                            capture_output=True, text=True)")
print("  print(grep_out.stdout)")
print()
print("Python's string methods beat grep/awk/sed for anything complex.")
print("Use subprocess for the FIRST command, Python for the processing.")
print()

embed(header="Checkpoint 2: piping — subprocess for capture, Python for filter")

# ============================================================================
# PATTERN 3: subprocess + collections
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: subprocess + collections together")
print("=" * 60)
print()
print("The real SRE pattern: capture → parse → analyse with collections.")
print()
print("TRY:")
print("  from collections import Counter, defaultdict")
print()
print("  # Get process list")
print("  r = subprocess.run(['ps', 'aux'], capture_output=True, text=True)")
print("  lines = r.stdout.strip().split('\\n')[1:]  # skip header")
print()
print("  # Count processes per user")
print("  users = Counter(line.split()[0] for line in lines)")
print("  print('Top 5 users by process count:')")
print("  for user, count in users.most_common(5):")
print("      print(f'  {user}: {count}')")
print()
print("  # Group process commands by user")
print("  by_user = defaultdict(list)")
print("  for line in lines:")
print("      parts = line.split(None, 10)  # split max 11 fields")
print("      if len(parts) >= 11:")
print("          by_user[parts[0]].append(parts[10][:60])")
print()
print("  # Show first 3 commands for the top user")
print("  top_user = users.most_common(1)[0][0]")
print("  print(f'\\nFirst 3 processes for {top_user}:')")
print("  for cmd in by_user[top_user][:3]:")
print("      print(f'  {cmd}')")
print()

from collections import Counter, defaultdict
embed(header="Checkpoint 3: subprocess + collections — process analysis")

# ============================================================================
# PATTERN 4: Building a health checker
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: Health check script")
print("=" * 60)
print()
print("Build a health checker that runs multiple diagnostic commands")
print("and produces a pass/fail report.")
print()
print("TYPE THIS OUT:")
print()
print("  checks = {")
print("      'disk_space': {")
print("          'cmd': ['df', '-h', '/'],")
print("          'check': lambda out: int(out.split('\\n')[1].split()[4].rstrip('%')) < 90")
print("      },")
print("      'hostname': {")
print("          'cmd': ['hostname'],")
print("          'check': lambda out: len(out.strip()) > 0")
print("      },")
print("      'python': {")
print("          'cmd': ['python3', '--version'],")
print("          'check': lambda out: 'Python 3' in out")
print("      },")
print("  }")
print()
print("  for name, spec in checks.items():")
print("      try:")
print("          r = subprocess.run(spec['cmd'], capture_output=True,")
print("                             text=True, timeout=5)")
print("          output = r.stdout + r.stderr  # some tools write to stderr")
print("          passed = spec['check'](output)")
print("          status = 'PASS' if passed else 'FAIL'")
print("      except Exception as e:")
print("          status = 'ERROR'")
print("          output = str(e)")
print("      print(f'  [{status}] {name}')")
print()

embed(header="Checkpoint 4: type out the health checker")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: Full SRE diagnostic tool")
print("=" * 60)
print()
print("Combine everything from this week. Build a function that:")
print()
print("  1. Runs these commands with subprocess:")
print("     - hostname")
print("     - uname -r")
print("     - uptime")
print("     - df -h /")
print("     - ps aux")
print()
print("  2. Uses Counter to count processes per user from ps aux")
print()
print("  3. Uses defaultdict to group disk mount points by usage tier:")
print("     <50% = 'healthy', 50-80% = 'warning', >80% = 'critical'")
print("     (parse df -h output for this)")
print()
print("  4. Handles all three failure modes")
print()
print("  5. Prints a clean report")
print()
print("All the pieces are in your hands. Assemble them.")
print()

embed(header="Checkpoint 5: build the full diagnostic tool")

print()
print("DAY 8 COMPLETE.")
print()
print("You now have the full subprocess + collections toolkit:")
print("  subprocess.run → capture → json.loads → Counter/defaultdict")
print("  No shell=True. No os.system. No Popen (yet).")
print()
print("Days 9-10: deeper subprocess (CompletedProcess, edge cases)")
print("Days 11-14: consolidation and integration challenges.")
