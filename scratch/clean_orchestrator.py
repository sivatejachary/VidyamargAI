import os

file_path = r"c:\Users\jshiv\Downloads\shivateja\backend\app\services\orchestrator.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for idx, line in enumerate(lines):
    if idx >= 520 and idx <= 540:
        if "except Exception as save_err:" in line:
            start_idx = idx
    if idx >= 1000 and idx <= 1040:
        if "# Helper to rebuild Candidate Profile Data" in line:
            end_idx = idx

print(f"Start index: {start_idx}, End index: {end_idx}")
if start_idx != -1 and end_idx != -1:
    new_lines = lines[:start_idx] + [
        "            except Exception as save_err:\n",
        '                logger.error(f"Failed to persist pipeline failure: {save_err}")\n\n'
    ] + lines[end_idx:]
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("Successfully replaced.")
else:
    print("Failed to find boundaries.")
