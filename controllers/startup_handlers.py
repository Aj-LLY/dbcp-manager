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

设计原则：
  - 单一职责：每个函数处理一种生命周期事件
  - 防御性编程：文件 I/O 和网络操作均包裹在 try/except 中
  - 用户友好：关闭前主动询问是否同步，启动时主动检测云端备份
  - 延迟导入：WebDAV 相关模块仅在需要时导入，避免启动时的依赖加载开销
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
# 工具栏扩展事件处理器 - 控制台和备份功能
# =============================================================================

def on_console(main_window):
    """打开控制台窗口，查看程序错误日志。

    创建一个只读的滚动文本窗口，以深色主题显示程序运行期间收集的错误日志。
    日志内容通过 error_log 模块的 get_errors() 函数获取。

    UI 设计：
      - 深色背景（#1e1e1e）配浅色文字（#d4d4d4），类似 VS Code 终端风格
      - 使用 Consolas 等宽字体，便于阅读日志
      - 文本区域为只读模式，防止意外修改
      - 提供"关闭"按钮退出窗口

    Args:
        main_window: MainWindow 实例，用作弹出对话框的父窗口

    Returns:
        None
    """
    # 创建模态子窗口
    dlg = tk.Toplevel(main_window)
    dlg.title("控制台 - 错误日志")  # 设置窗口标题
    dlg.geometry("700x400")  # 固定窗口尺寸：宽 700px，高 400px
    dlg.configure(bg="#1e1e1e")  # 深色底色

    # 创建带滚动条的文本组件
    text = scrolledtext.ScrolledText(dlg, bg="#1e1e1e", fg="#d4d4d4",
        insertbackground="white",  # 光标颜色
        font=("Consolas", 9),  # 等宽字体
        wrap="word")  # 按单词换行
    text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)  # 填充窗口并留出边距

    # 获取错误日志并插入文本框顶部
    text.insert("1.0", get_errors())
    # 将文本框设为只读，允许选中复制但不允许编辑
    text.configure(state="disabled")

    # 关闭按钮（深色风格，匹配控制台主题）
    btn = tk.Button(dlg, text="关闭", command=dlg.destroy,
        bg="#333", fg="#ccc", cursor="hand2")
    btn.pack(pady=(0, 4))  # 底部留 4px 间距


def on_backup(main_window):
    """处理"WebDAV备份"按钮点击事件。

    打开 WebDAV 备份对话框，允许用户执行以下操作：
      - 上传备份：将当前本地数据文件同步到 WebDAV 服务器
      - 查看备份列表：浏览远程服务器上已有的备份文件
      - 恢复备份：选择一个远程备份文件恢复到本地

    恢复回调设计：
      当用户在备份对话框中执行恢复操作后，通过 on_restore 回调触发：
      1. 重新加载数据文件（覆盖内存中的旧数据）
      2. 刷新看板（UI 反映恢复后的数据状态）

    Args:
        main_window: MainWindow 实例，提供以下访问入口：
            - _data_service: 数据持久化服务（提供 reload 方法）
            - _refresh_kanban: 看板刷新方法

    Returns:
        None
    """
    # 创建备份对话框，传入当前数据文件的路径
    dialog = BackupDialog(main_window, Config.get_data_file_path())
    # 设置恢复回调：当用户执行恢复操作后重新加载数据并刷新看板
    dialog.on_restore = lambda: (main_window._data_service.reload(), main_window._refresh_kanban())
    # 阻塞等待备份对话框关闭（模态窗口）
    main_window.wait_window(dialog)


# =============================================================================
# 窗口生命周期事件处理器 - 启动和关闭
# =============================================================================

def on_close(main_window):
    """窗口关闭前执行数据保存、窗口位置记录，并询问是否同步到 WebDAV。

    执行流程：
      1. 保存当前数据到本地 JSON 文件（防止数据丢失）
      2. 保存窗口的位置和大小到 window_geometry.json（下次启动恢复窗口布局）
      3. 检查是否已配置 WebDAV：
         - 已配置：弹窗询问用户是否将数据同步到 WebDAV 服务器
         - 未配置：跳过同步步骤
      4. 如果用户确认同步，执行 WebDAV 备份操作
      5. 销毁窗口，终止应用程序

    异常处理设计：
      - 窗口几何信息保存失败：静默忽略（非关键功能，不应阻断关闭流程）
      - WebDAV 同步失败：弹窗显示错误信息，仍允许关闭窗口（同步是可选的）

    Args:
        main_window: MainWindow 实例，提供以下访问入口：
            - _data_service: 数据持久化服务（save 方法）
            - geometry(): tkinter 窗口几何信息获取方法
            - destroy(): 窗口销毁方法

    Returns:
        None
    """
    # --- 第一步：保存当前数据 ---
    main_window._data_service.save()

    # --- 第二步：保存窗口位置和大小 ---
    try:
        import json, os
        # 获取窗口当前几何信息（格式：width x height + x + y）
        geo = main_window.geometry()
        # 构造窗口几何信息存储路径：data_dir/data/window_geometry.json
        path = os.path.join(Config.get_data_dir(), "data", "window_geometry.json")
        # 确保父目录存在
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # 写入 JSON 文件
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"geometry": geo}, f)
    except Exception:
        # 静默忽略：窗口位置保存失败不影响程序正常关闭
        pass

    # --- 第三步：询问是否同步到 WebDAV ---
    # 延迟导入 WebDAV 配置和备份服务（避免启动时的模块加载开销）
    from utils.webdav_config import WebDAVConfig
    cfg = WebDAVConfig.load()  # 加载持久化的 WebDAV 配置

    if cfg.url:
        # WebDAV 已配置：弹出确认对话框询问是否同步
        if messagebox.askyesno("数据同步", "是否将当前数据同步到 WebDAV 服务器？"):
            try:
                from services.backup_service import BackupService
                # 创建备份服务实例并执行备份
                svc = BackupService(cfg)
                ok, msg = svc.backup(Config.get_data_file_path())
                if ok:
                    messagebox.showinfo("同步成功", f"数据已备份: {msg}")
                else:
                    messagebox.showwarning("同步失败", msg)
            except Exception as e:
                # 网络异常等：提示用户但不阻断关闭流程
                messagebox.showwarning("同步错误", str(e))

    # --- 第四步：销毁窗口 ---
    main_window.destroy()


def check_restore_on_startup(main_window):
    """启动时检查 WebDAV 备份，提示用户是否从云端恢复数据。

    在应用程序启动后调用此函数，检查 WebDAV 服务器上是否存在备份文件。
    如果存在，弹窗列出可用备份文件供用户选择恢复。

    执行流程：
      1. 加载 WebDAV 配置，检查 URL 是否已配置
         - 未配置：直接返回，不弹窗（静默跳过）
      2. 通过 BackupService 获取远程备份文件列表
         - 无备份或请求失败：直接返回
      3. 弹出备份列表对话框：
         - 显示最近 20 个备份文件（按名称倒序）
         - 用户选择备份文件后，二次确认恢复操作
      4. 验证备份文件格式（JSON 有效性检查）
      5. 写入本地数据文件并重新加载，刷新看板

    安全性设计：
      - 恢复前验证 JSON 格式：防止写入无效数据导致程序无法启动
      - 二次确认：明确警告当前数据将被覆盖
      - 异常静默捕获：启动阶段的网络异常不应阻塞程序正常启动

    Args:
        main_window: MainWindow 实例，提供以下访问入口：
            - _data_service: 数据持久化服务（reload 方法）
            - _refresh_kanban: 看板刷新方法

    Returns:
        None

    Raises:
        无显式抛出异常：所有异常在内部静默捕获
    """
    # --- 第一步：检查 WebDAV 配置 ---
    # 延迟导入以避免非必需模块的启动加载开销
    from utils.webdav_config import WebDAVConfig
    cfg = WebDAVConfig.load()

    if not cfg.url:
        # WebDAV 未配置，静默跳过（大多数用户不一定会配置 WebDAV）
        return

    try:
        # --- 第二步：获取远程备份列表 ---
        from services.backup_service import BackupService
        svc = BackupService(cfg)
        ok, msg, files = svc.list_backups()

        if not ok or not files:
            # 无备份文件或请求失败，静默跳过
            return

        # 按文件名倒序排列，最新的备份显示在最前面
        files.sort(key=lambda x: x["name"], reverse=True)

        # --- 第三步：构建备份列表对话框 ---
        dlg = tk.Toplevel(main_window)
        dlg.title("数据恢复 - 检测到云端备份")
        dlg.geometry("550x400")
        dlg.configure(bg="#ffffff")
        dlg.grab_set()  # 设为模态，阻止对主窗口的操作

        # 标题提示
        tk.Label(dlg, text="检测到以下云端备份，是否恢复？", bg="#ffffff",
                 font=("Microsoft YaHei", 12, "bold"), fg="#2c3e50",
                 ).pack(pady=(15, 10))

        # 备份列表框架（Listbox + Scrollbar）
        frame = tk.Frame(dlg, bg="#ffffff")
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # 单选模式的备份文件列表
        lb = tk.Listbox(frame, font=("Microsoft YaHei", 10), selectmode="single")
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 垂直滚动条
        sb = tk.Scrollbar(frame, orient=tk.VERTICAL, command=lb.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb.configure(yscrollcommand=sb.set)  # 关联滚动条

        # 填充备份文件列表（最多显示 20 个，避免列表过长）
        for f in files[:20]:
            # 显示格式：文件名  (修改时间)
            lb.insert(tk.END, f"{f['name']}  ({f.get('modified','?')})")

        # 使用可变容器在闭包中传递恢复状态
        result = {"selected": False}

        def _restore():
            """恢复按钮回调：执行数据恢复操作。

            包含以下步骤：
              1. 获取用户选中的备份索引
              2. 二次确认（警告当前数据将被覆盖）
              3. 从 WebDAV 下载备份文件内容
              4. 验证 JSON 格式有效性
              5. 写入本地数据文件
              6. 重新加载数据并刷新看板
              7. 关闭对话框
            """
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning("提示", "请选择要恢复的备份", parent=dlg)
                return

            idx = sel[0]  # 获取选中项索引

            # 二次确认：警告用户当前数据将被覆盖
            if messagebox.askyesno("确认恢复",
                                   f"确定要恢复「{files[idx]['name']}」吗？\n当前数据将被覆盖！",
                                   parent=dlg):
                # 从 WebDAV 下载选中的备份文件
                ok2, msg2, body = svc.restore(files[idx]["path"])
                if ok2:
                    # --- 验证备份文件 JSON 格式 ---
                    try:
                        json.loads(body.decode("utf-8"))
                    except Exception:
                        # JSON 解析失败，拒绝写入无效数据
                        messagebox.showerror("错误", "备份文件格式错误", parent=dlg)
                        return

                    # --- 写入本地数据文件 ---
                    with open(Config.get_data_file_path(), "wb") as wf:
                        wf.write(body)

                    # --- 重新加载数据并刷新 UI ---
                    main_window._data_service.reload()
                    main_window._refresh_kanban()
                    result["selected"] = True
                    messagebox.showinfo("成功", "数据已恢复", parent=dlg)
                    dlg.destroy()
                else:
                    # 网络错误、权限不足等
                    messagebox.showerror("恢复失败", msg2, parent=dlg)

        # --- 底部按钮区域 ---
        btn_frame = tk.Frame(dlg, bg="#f0f2f5")
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # 顶部分割线
        tk.Frame(btn_frame, bg="#d0d5dd", height=1).pack(fill=tk.X)

        inner = tk.Frame(btn_frame, bg="#f0f2f5")
        inner.pack(fill=tk.X, padx=16, pady=8)

        # 跳过按钮（白色背景，靠右）
        tk.Button(inner, text="跳过", command=dlg.destroy,
            bg="#ffffff", fg="#2c3e50", cursor="hand2",
            font=("Microsoft YaHei", 10), relief="flat", padx=18, pady=5,
            highlightbackground="#d0d5dd", highlightthickness=1,
            ).pack(side=tk.RIGHT, padx=(10, 0))

        # 恢复选中按钮（蓝色背景，白色文字，靠右）
        tk.Button(inner, text="恢复选中", command=_restore,
            bg="#3498db", fg="white", cursor="hand2",
            font=("Microsoft YaHei", 10, "bold"), relief="flat", padx=18, pady=5,
            ).pack(side=tk.RIGHT)

        # 阻塞等待对话框关闭
        main_window.wait_window(dlg)
    except Exception:
        # 静默捕获所有异常：网络不可用、配置错误等不应阻塞程序正常启动
        pass
