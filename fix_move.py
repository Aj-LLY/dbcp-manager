import os
path = os.path.join(os.path.dirname(__file__), 'ui', 'detail_dialog.py')
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the two messagebox.showinfo lines and add protection
for i, line in enumerate(lines):
    if 'messagebox.showinfo("提示", "已经是第一个阶段"' in line:
        # Insert before this line
        lines.insert(i, '            self._opening_child = True  # 防止messagebox抢焦点导致FocusOut关闭\n')
        # Insert after this line
        lines.insert(i+2, '            self._opening_child = False\n')
    if 'messagebox.showinfo("提示", "已经是最后一个阶段"' in line:
        lines.insert(i, '            self._opening_child = True  # 防止messagebox抢焦点导致FocusOut关闭\n')
        lines.insert(i+2, '            self._opening_child = False\n')

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Protection added to move handlers')
