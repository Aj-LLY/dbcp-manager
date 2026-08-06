"""
重命名关键词编辑对话框 — 自定义修改文件识别关键字。
"""
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox

from utils.config import Config


def show_keywords_dialog(parent):
    """显示重命名关键词编辑对话框。"""
    kw_path = os.path.join(Config.get_data_dir(), "data", "rename_keywords.json")

    # 内置默认关键词（与 rename.py 保持一致）
    _DEFAULT_KEYWORDS = [
        ["保密承诺书", "02", "保密承诺书", True],
        ["测评调研表", "03", "测评调研表", False],
        ["测评授权书", "04", "测评授权书", True],
        ["风险告知书", "05", "风险告知书", True],
        ["项目计划书", "06", "项目计划书", False],
        ["测评方案", "07", "测评方案", False],
        ["归档材料评审记录表", "08", "测评方案评审表", False],
        ["测评方案评审表", "08", "测评方案评审表", False],
        ["首次会议记录", "09", "首次会议记录", True],
        ["测评现场记录表", "10", "测评现场记录表", False],
        ["问题汇总", "11", "问题汇总及整改建设书", False],
        ["漏洞扫描报告", "12", "漏洞扫描报告", False],
        ["项目文档移交清单", "14", "项目文档移交清单", True],
        ["末次会议记录", "15", "末次会议记录", True],
        ["测评报告-终稿", "16", "测评报告-终稿", False],
        ["测评报告评审记录表", "17", "测评报告评审表", False],
        ["测评报告评审表", "17", "测评报告评审表", False],
        ["服务情况评价表", "18", "服务情况评价表", True],
        ["报备表", "19", "报备表", True],
        ["渗透测试报告", "13", "渗透测试报告", False],
    ]

    # 优先从 JSON 配置文件加载，文件不存在或为空则使用内置默认值
    try:
        with open(kw_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            loaded = data.get("keywords", [])
            keywords = loaded if loaded else _DEFAULT_KEYWORDS
    except Exception:
        keywords = _DEFAULT_KEYWORDS

    dlg = tk.Toplevel(parent)
    dlg.title("自定义重命名关键词")
    dlg.geometry("750x550")
    dlg.configure(bg="white")

    # Treeview
    cols = ("关键词", "编号", "标准名称", "公司级")
    tree = ttk.Treeview(dlg, columns=cols, show="headings", height=18)
    tree.heading("关键词", text="关键词")
    tree.heading("编号", text="编号")
    tree.heading("标准名称", text="标准名称")
    tree.heading("公司级", text="公司级")
    tree.column("关键词", width=200)
    tree.column("编号", width=60)
    tree.column("标准名称", width=180)
    tree.column("公司级", width=60)
    tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def refresh():
        tree.delete(*tree.get_children())
        for kw in keywords:
            tree.insert("", "end", values=kw)

    refresh()

    # Edit frame
    edit_frame = tk.Frame(dlg, bg="white")
    edit_frame.pack(fill=tk.X, padx=10, pady=5)

    row = tk.Frame(edit_frame, bg="white")
    row.pack(fill=tk.X)
    tk.Label(row, text="关键词", bg="white").pack(side=tk.LEFT)
    v_kw = tk.StringVar()
    tk.Entry(row, textvariable=v_kw, width=20).pack(side=tk.LEFT, padx=5)
    tk.Label(row, text="编号", bg="white").pack(side=tk.LEFT)
    v_num = tk.StringVar()
    tk.Entry(row, textvariable=v_num, width=5).pack(side=tk.LEFT, padx=5)
    tk.Label(row, text="标准名", bg="white").pack(side=tk.LEFT)
    v_name = tk.StringVar()
    tk.Entry(row, textvariable=v_name, width=20).pack(side=tk.LEFT, padx=5)
    v_co = tk.BooleanVar()
    tk.Checkbutton(row, text="公司级", variable=v_co, bg="white").pack(side=tk.LEFT, padx=5)

    def add():
        kw, num, name = v_kw.get().strip(), v_num.get().strip(), v_name.get().strip()
        if kw and num and name:
            keywords.append([kw, num, name, v_co.get()])
            refresh()
    def edit():
        sel = tree.selection()
        if sel:
            item = tree.item(sel[0])
            idx = tree.index(sel[0])
            keywords[idx] = [v_kw.get().strip(), v_num.get().strip(),
                            v_name.get().strip(), v_co.get()]
            refresh()
    def delete():
        sel = tree.selection()
        if sel:
            idx = tree.index(sel[0])
            del keywords[idx]
            refresh()
    def on_select(e):
        sel = tree.selection()
        if sel:
            vals = tree.item(sel[0])["values"]
            v_kw.set(vals[0])
            v_num.set(vals[1])
            v_name.set(vals[2])
            v_co.set(vals[3] == "True" or vals[3] is True)
    tree.bind("<<TreeviewSelect>>", on_select)

    btn_row = tk.Frame(edit_frame, bg="white")
    btn_row.pack(fill=tk.X, pady=5)
    for t, c in [("添加", add), ("修改", edit), ("删除", delete)]:
        tk.Button(btn_row, text=t, command=c, bg="#3498db", fg="white",
                  relief="flat", padx=10).pack(side=tk.LEFT, padx=2)

    def save_and_close():
        os.makedirs(os.path.dirname(kw_path), exist_ok=True)
        data = {"keywords": keywords}
        with open(kw_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("提示", "关键词已保存", parent=dlg)
        dlg.destroy()

    tk.Frame(dlg, bg="#d0d5dd", height=1).pack(fill=tk.X)
    btn_bar = tk.Frame(dlg, bg="#f0f2f5")
    btn_bar.pack(fill=tk.X, padx=16, pady=8)
    tk.Button(btn_bar, text="取消", command=dlg.destroy, bg="white",
              relief="flat", padx=16).pack(side=tk.RIGHT, padx=(10, 0))
    tk.Button(btn_bar, text="保存", command=save_and_close, bg="#3498db",
              fg="white", relief="flat", padx=16).pack(side=tk.RIGHT)
