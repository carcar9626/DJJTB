You are acting as a plain-English repository auditor helping me clean up my custom utility scripts.

Your job is to read them, compare them, and explain them without using overly dense jargon in a .md file created in root.

CRITICAL RULES:
1. Do NOT generate or rewrite any code.
2. Speak in casual, day-to-day English.
3. Identify if a script looks like an incomplete experiment, a hardcoded temporary fix, or a complete operational file.

Please analyze the provided files and break your response down into these three clear sections:

### 📂 Script Profiles
What is its core job? Does it look fully functional? Note any unique triggers or external hooks it uses.

### 🔄 The Key Differences
* Explain exactly what sets these versions apart in plain terms (e.g., "Version A uses live console inputs, while Version B has everything hardcoded," or "Version A includes a specific face-fusion/host argument that Version B leaves out"). Which version, if any, is current active (cross reference with @djjtb.py)

### 🧹 Clean-Up Recommendation
* **Keep/Primary**: Which file looks like the master or the most "unified" version I should carry forward?
* **Archive/Delete**: Which files look like redundant variations, older legacy attempts, backups or temporary tests that can be safely discarded?