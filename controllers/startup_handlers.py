"""
启动与关闭事件处理函数模块 - 从 MainWindow 中抽取的 WebDAV 同步和窗口生命周期处理器

本模块包含与应用程序启动、关闭、备份相关的所有事件处理函数，采用函数式风格：
  - 每个函数以 MainWindow 实例作为第一个参数（main_window）
  - 通过 main_window 访问所有服务层和 UI 组件（._data_service 等）

主要功能：
  1. 控制台查看（错误日志）
  2. WebDAV 远程备份管理
  3. 窗口关闭前的数据保存和同步提示
  4. 启动时的云端备份恢复检查
"""

# =============================================================================
# 导入区
# =============================================================================

import json  # JSON 格式解析，用于验证恢复数据的格式
import tkinter as tk  # Python 标准 GUI 库
from tkinter import messagebox  # 消息弹窗组件
from tkinter import scrolledtext  # 带滚动条的文本组件，用于控制台日志显示

from ui.backup_dialog import BackupDialog  # WebDAV 备份对话框类
from utils.config import Config  # 全局配置类
from utils.error_log import get_errors  # 获取错误日志内容的函数


# =============================================================================
# 工具栏扩展事件处理器
# =============================================================================

def on_console(main_window):
    """打开控制台窗口，查看程序错误日志"""
    dlg = tk.Toplevel(main_window)
    dlg.title("控制台 - 错误日志")
    dlg.geometry("700x400")
    dlg.configure(bg="#1e1e1e")
    text = scrolledtext.ScrolledText(dlg, bg="#1e1e1e", fg="#d4d4d4",
        insertbackground="white", font=("Consolas", 9), wrap="word")
    text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
    text.insert("1.0", get_errors())
    text.configure(state="disabled")
    btn = tk.Button(dlg, text="关闭", command=dlg.destroy,
        bg="#333", fg="#ccc", cursor="hand2")
    btn.pack(pady=(0, 4))


def on_backup(main_window):
    """处理"WebDAV备份"按钮点击事件"""
    dialog = BackupDialog(main_window, Config.get_data_file_path())  # 创建备份对话框，传入数据文件路径
    # 设置恢复回调：当用户执行恢复操作后，重新加载数据文件并刷新看板
    dialog.on_restore = lambda: (main_window._data_service.reload(), main_window._refresh_kanban())
    main_window.wait_window(dialog)  # 等待备份对话框关闭


# =============================================================================
# 窗口生命周期事件处理器
# =============================================================================

def on_close(main_window):
    """窗口关闭前保存数据、窗口位置，并询问是否同步到 WebDAV。"""
    main_window._data_service.save()
    # 保存窗口位置和大小
    try:
        import json, os
        geo = main_window.geometry()
        path = os.path.join(Config.get_data_dir(), "data", "window_geometry.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"geometry": geo}, f)
    except Exception:
        pass
    # 询问是否备份到 WebDAV
    from utils.webdav_config import WebDAVConfig
    cfg = WebDAVConfig.load()
    if cfg.url:
        if messagebox.askyesno("数据同步", "是否将当前数据同步到 WebDAV 服务器？"):
            try:
                from services.backup_service import BackupService
                svc = BackupService(cfg)
                ok, msg = svc.backup(Config.get_data_file_path())
                if ok:
                    messagebox.showinfo("同步成功", f"数据已备份: {msg}")
                else:
                    messagebox.showwarning("同步失败", msg)
            except Exception as e:
                messagebox.showwarning("同步错误", str(e))
    main_window.destroy()


def check_restore_on_startup(main_window):
    """启动时检查 WebDAV 备份，提示是否恢复数据。"""
    from utils.webdav_config import WebDAVConfig
    cfg = WebDAVConfig.load()
    if not cfg.url:
        return
    try:
        from services.backup_service import BackupService
        svc = BackupService(cfg)
        ok, msg, files = svc.list_backups()
        if not ok or not files:
            return
        files.sort(key=lambda x: x["name"], reverse=True)
        # 构建备份列表对话框
        dlg = tk.Toplevel(main_window)
        dlg.title("数据恢复 - 检测到云端备份")
        dlg.geometry("550x400")
        dlg.configure(bg="#ffffff")
        dlg.grab_set()
        tk.Label(dlg, text="检测到以下云端备份，是否恢复？", bg="#ffffff",
                 font=("Microsoft YaHei", 12, "bold"), fg="#2c3e50",
                 ).pack(pady=(15, 10))
        frame = tk.Frame(dlg, bg="#ffffff")
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        lb = tk.Listbox(frame, font=("Microsoft YaHei", 10), selectmode="single")
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(frame, orient=tk.VERTICAL, command=lb.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb.configure(yscrollcommand=sb.set)
        for f in files[:20]:
            lb.insert(tk.END, f"{f['name']}  ({f.get('modified','?')})")
        result = {"selected": False}
        def _restore():
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning("提示", "请选择要恢复的备份", parent=dlg)
                return
            idx = sel[0]
            if messagebox.askyesno("确认恢复", f"确定要恢复「{files[idx]['name']}」吗？\n当前数据将被覆盖！", parent=dlg):
                ok2, msg2, body = svc.restore(files[idx]["path"])
                if ok2:
                    try:
                        json.loads(body.decode("utf-8"))
                    except Exception:
                        messagebox.showerror("错误", "备份文件格式错误", parent=dlg)
                        return
                    with open(Config.get_data_file_path(), "wb") as wf:
                        wf.write(body)
                    main_window._data_service.reload()
                    main_window._refresh_kanban()
                    result["selected"] = True
                    messagebox.showinfo("成功", "数据已恢复", parent=dlg)
                    dlg.destroy()
                else:
                    messagebox.showerror("恢复失败", msg2, parent=dlg)
        btn_frame = tk.Frame(dlg, bg="#f0f2f5")
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Frame(btn_frame, bg="#d0d5dd", height=1).pack(fill=tk.X)
        inner = tk.Frame(btn_frame, bg="#f0f2f5")
        inner.pack(fill=tk.X, padx=16, pady=8)
        tk.Button(inner, text="跳过", command=dlg.destroy,
            bg="#ffffff", fg="#2c3e50", cursor="hand2",
            font=("Microsoft YaHei", 10), relief="flat", padx=18, pady=5,
            highlightbackground="#d0d5dd", highlightthickness=1,
            ).pack(side=tk.RIGHT, padx=(10, 0))
        tk.Button(inner, text="恢复选中", command=_restore,
            bg="#3498db", fg="white", cursor="hand2",
            font=("Microsoft YaHei", 10, "bold"), relief="flat", padx=18, pady=5,
            ).pack(side=tk.RIGHT)
        main_window.wait_window(dlg)
    except Exception:
        pass
