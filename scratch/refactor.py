import os
import re

directory = "/home/hastur/Code/YGO/yugioh-ai/ygo/envs/message_handlers"
line_to_insert = "from ygo.envs.duel import register_message"

# Regular expression pattern to match the lines to be replaced
pattern = r"MESSAGES\s*=\s*{([^}]*)}"

# Iterate over all files in the directory
file_names = list(os.listdir(directory))
file_names.sort()
for filename in file_names:
    if filename.endswith(".py"):
        base = os.path.splitext(filename)[0]
        print("from . import " + base)

        # file_path = os.path.join(directory, filename)

        # # Read the contents of the file
        # with open(file_path, 'r') as file:
        #     lines = file.readlines()

        # modified_lines = []

        # should_insert = False

        # # Search for the lines to be replaced and modify them
        # for line in lines:
        #     if re.search(pattern, line):
        #         modified_line = re.sub(pattern, r"register_message({\1})", line)
        #         modified_lines.append(modified_line)
        #         should_insert = True
        #     else:
        #         modified_lines.append(line)

        # # Insert the line at the beginning of the file if necessary
        # if modified_lines and not modified_lines[0].startswith(line_to_insert) and should_insert:
        #     modified_lines.insert(0, line_to_insert + "\n")

        # # Write the modified contents back to the file
        # with open(file_path, 'w') as file:
        #     file.writelines(modified_lines)