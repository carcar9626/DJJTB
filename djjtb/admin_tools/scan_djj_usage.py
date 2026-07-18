#!/usr/bin/env python3
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

script_dir = Path(__file__).resolve().parent
output_dir = script_dir / "Reports" / "Usage"
output_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
usage_output = output_dir / f"djj_usage_report_{timestamp}.txt"

project_root = Path.cwd()

# === Part 1: djj.function usage report ===
usage_pattern = re.compile(r'djj\.([a-zA-Z_][a-zA-Z0-9_]*)')
usage = defaultdict(set)


for filepath in project_root.rglob("*.py"):
    if filepath.name in {usage_output.name, "djj_utils_audit.py"}:
        continue
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            for match in usage_pattern.findall(line):
                usage[match].add(str(filepath.relative_to(project_root)))

with open(usage_output, "w", encoding="utf-8") as out:
    for func in sorted(usage.keys()):
        out.write(f"🔹 djj.{func} ({len(usage[func])} file(s)):\n")
        for filename in sorted(usage[func]):
            out.write(f"   - {filename}\n")
        out.write("\n")

print(f"✅ Usage report saved to: {usage_output.resolve()}")

# === Part 2: Bad import detection ===
violations_output = Path("djj_import_violations.txt")
import_pattern = re.compile(r'^from\s+(djjtb\.utils|utils)\s+import\b')
violations = []

for filepath in project_root.rglob("*.py"):
    if filepath.name in {violations_output.name, "djj_utils_audit.py"}:
        continue
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            if import_pattern.search(line):
                violations.append(f"{filepath.relative_to(project_root)}:{i}: {line.strip()}")

with open(violations_output, "w", encoding="utf-8") as out:
    if violations:
        out.write("❌ Found non-compliant utils imports:\n\n")
        out.write("\n".join(violations))
    else:
        out.write("✅ No violations found.\n")

print(f"✅ Import check saved to: {violations_output.resolve()}")