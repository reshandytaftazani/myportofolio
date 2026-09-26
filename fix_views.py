import re

with open('main/views.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_show_main = False
for line in lines:
    if line.startswith("def show_main(request):"):
        in_show_main = True
    elif line.startswith("def "):
        in_show_main = False

    if '"last_login": last_login,' in line:
        if in_show_main:
            new_lines.append(line)
        else:
            pass # skip adding this line
    else:
        new_lines.append(line)

with open('main/views.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
