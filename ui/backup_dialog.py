"""
WebDAV 备份管理对话框模块 -- 等保测评进度管理系统

本模块提供数据备份与恢复的 WebDAV 管理界面，以模态对话框形式呈现。
使用 ttk.Notebook 标签页组织两个主要功能区域：

标签页一 -- 服务器配置：
  - 配置 WebDAV 服务器连接信息（地址、用户名、密码、远程路径）
  - 测试 WebDAV 连接是否可用
  - 保存配置到本地文件（WebDAVConfig）

标签页二 -- 备份与恢复：
  - 立即备份：将当前本地数据文件上传到远端服务器
  - 刷新列表：获取远端所有备份文件并显示在 Treeview 中
  - 恢复选中：下载远端备份文件，验证 JSON 格式后覆盖本地数据
  - 删除选中：删除远端的某个备份文件

所有备份文件存储在 WebDAV 服务器的指定远程路径下，
文件名为备份时的时间戳。恢复前会对下载内容进行 JSON 格式验证。
"""

# =============================================================================
# 标准库导入
# =============================================================================
import json                     # JSON 序列化 / 反序列化：用于验证备份文件的数据格式
import tkinter as tk            # Tkinter GUI 库：构建桌面应用窗口和组件
from tkinter import ttk, messagebox  # ttk 增强组件（Notebook 等）| messagebox 弹窗 / 确认

# =============================================================================
# 项目内部模块导入
# =============================================================================
from utils.config import Config            # 全局配置：字体族、字号等 UI 常量
from ui.widget_base import center_window    # 窗口居中工具函数
from utils.webdav_config import WebDAVConfig  # WebDAV 配置管理：加载 / 保存服务器连接信息
from utils.helpers import bordered_entry   # 辅助函数：创建带灰色外边框的输入框
from services.backup_service import BackupService  # 备份服务：WebDAV 上传 / 下载 / 列表 / 删除操作


# =============================================================================
# BackupDialog -- WebDAV 备份管理模态对话框
# =============================================================================

class BackupDialog(tk.Toplevel):
    """WebDAV 备份管理对话框。

    以模态顶层窗口形式提供 WebDAV 服务器配置和数据备份/恢复功能。
    使用 ttk.Notebook 分两个标签页：

    配置标签页：
      - 服务器地址输入
      - 用户名输入
      - 密码输入（显示掩码 *）
      - 远程备份路径输入
      - 测试连接按钮 + 保存配置按钮
      - 连接状态提示标签

    备份恢复标签页：
      - 立即备份按钮 + 操作状态提示
      - 远端文件列表（Treeview，文件名 + 修改时间）
      - 刷新列表按钮
      - 恢复选中按钮 + 删除选中按钮
      - 关闭按钮

    Attributes:
        on_restore: callable | None
            恢复数据后的回调函数，由 MainWindow 设置。用于在数据恢复后
            通知主窗口重新加载数据并刷新界面。
    """

    def __init__(self, parent, data_file_path: str):
        """初始化备份管理对话框。

        加载已保存的 WebDAV 配置，创建 BackupService 服务实例，
        构建标签页 UI，并将配置填入对应表单字段。

        Args:
            parent: 父级窗口。
            data_file_path: 本地数据文件的完整路径（用于备份上传和恢复下载）。
        """
        # 调用父类 Tk.Toplevel 构造器
        super().__init__(parent)
        self.title("WebDAV 备份管理")                          # 设置窗口标题
        self._data_file = data_file_path                       # 保存本地数据文件路径
        self._cfg = WebDAVConfig.load()                        # 从配置文件加载已保存的 WebDAV 配置
        self._svc = BackupService(self._cfg)                   # 使用当前配置创建备份服务实例

        self.on_restore = None                                 # 恢复后的回调（由 MainWindow 设置）

        # ---- 按顺序执行初始化步骤 ----
        self._setup_window()     # ① 配置窗口基本属性
        self._build_ui()         # ② 构建标签页 UI 布局
        self._load_config()      # ③ 将已保存配置加载到表单输入框
        center_window(self)       # ④ 窗口居中
        self.grab_set()          # ⑤ 设为模态窗口

    def _setup_window(self):
        """配置对话框窗口的基本属性。

        初始大小 560×550，最小尺寸 480×420，可调整大小，白色背景。
        """
        self.geometry("560x550")         # 初始窗口大小
        self.minsize(480, 420)           # 最小尺寸
        self.resizable(True, True)       # 允许调整大小
        self.configure(bg="#ffffff")     # 白色背景

    def _build_ui(self):
        """构建标签页 UI 框架。

        使用 Canvas + Scrollbar 包裹 Notebook，确保窗口缩小时内容可滚动访问。
        Notebook 包含两个标签页：
          - "服务器配置"：服务器连接参数配置
          - "备份 & 恢复"：备份/恢复操作界面
        """
        # 可滚动画布，白色背景，无高亮边框
        canvas = tk.Canvas(self, bg="#ffffff", highlightthickness=0)
        # 垂直滚动条，绑定到 Canvas 的 yview
        scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)         # 双向绑定

        # 创建 Notebook 并放置到 Canvas 中
        nb = ttk.Notebook(canvas)
        canvas.create_window((0, 0), window=nb, anchor="nw", tags="nb_win")

        # Notebook 大小变化时更新 Canvas 滚动区域和窗口宽度
        def _on_nb_configure(event):
            """Notebook 配置变化事件：更新 Canvas 滚动区域和窗口宽度。"""
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig("nb_win", width=canvas.winfo_width() - 4)
        nb.bind("<Configure>", _on_nb_configure)
        # Canvas 宽度变化时同步窗口宽度
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("nb_win", width=e.width - 4))

        # 鼠标滚轮事件处理
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta/120), "units"))

        # 布局：滚动条右侧垂直填充，Canvas 填充左侧剩余空间
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        # ---- 标签页一：本地备份 ----
        self._local_frame = tk.Frame(nb, bg="#ffffff")
        nb.add(self._local_frame, text="  本地备份  ")
        self._build_local_backup_tab()

        # ---- 标签页二：服务器配置 ----
        self._config_frame = tk.Frame(nb, bg="#ffffff")
        nb.add(self._config_frame, text="  服务器配置  ")
        self._build_config_tab()

        # ---- 标签页三：备份恢复 ----
        self._action_frame = tk.Frame(nb, bg="#ffffff")
        nb.add(self._action_frame, text="  备份 & 恢复  ")
        self._build_action_tab()
        # 切换标签页时自动刷新备份列表
        nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)


    def _build_local_backup_tab(self):
        """构建本地备份标签页 — 显示 data/backup/ 中的备份文件。"""
        import os
        import shutil
        from datetime import datetime

        f = self._local_frame
        tk.Label(f, text="本地自动备份", bg="white", fg="#2c3e50",
                 font=("Microsoft YaHei", 14, "bold")).pack(anchor="w", pady=(0, 5))
        tk.Label(f, text="每次关闭程序时自动备份，保留最近30个备份文件",
                 bg="white", fg="#7f8c8d",
                 font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(0, 10))

        backup_dir = os.path.join(Config.get_data_dir(), "data", "backup")
        os.makedirs(backup_dir, exist_ok=True)

        # Treeview
        cols = ("文件名", "大小", "修改时间")
        tree = ttk.Treeview(f, columns=cols, show="headings", height=12)
        for c, w in [("文件名", 250), ("大小", 80), ("修改时间", 150)]:
            tree.heading(c, text=c)
            tree.column(c, width=w)
        tree.pack(fill=tk.BOTH, expand=True, pady=5)

        def refresh_local():
            tree.delete(*tree.get_children())
            try:
                files = sorted(os.listdir(backup_dir), reverse=True)
                for fn in files:
                    fp = os.path.join(backup_dir, fn)
                    sz = os.path.getsize(fp)
                    mt = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M")
                    tree.insert("", "end", values=(fn, f"{sz/1024:.1f}KB", mt))
            except Exception:
                pass

        refresh_local()

        btn_row = tk.Frame(f, bg="white")
        btn_row.pack(fill=tk.X, pady=10)
        tk.Button(btn_row, text="刷新", command=refresh_local,
                  bg="#3498db", fg="white", relief="flat", padx=12, cursor="hand2",
                  font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(0, 5))

        def restore_local():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("提示", "请先选择要恢复的备份文件", parent=self)
                return
            fn = tree.item(sel[0])["values"][0]
            src = os.path.join(backup_dir, fn)
            dst = Config.get_data_file_path()
            if not messagebox.askyesno("确认恢复", f"将用 {fn} 覆盖当前数据，确定？", parent=self):
                return
            try:
                shutil.copy2(src, dst)
                self._on_restore()
                messagebox.showinfo("成功", "本地备份已恢复", parent=self)
            except Exception as e:
                messagebox.showerror("错误", str(e), parent=self)

        tk.Button(btn_row, text="恢复选中", command=restore_local,
                  bg="#27ae60", fg="white", relief="flat", padx=12, cursor="hand2",
                  font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(0, 5))

        def delete_local():
            sel = tree.selection()
            if not sel:
                return
            fn = tree.item(sel[0])["values"][0]
            if messagebox.askyesno("确认删除", f"删除 {fn}？", parent=self):
                try:
                    os.remove(os.path.join(backup_dir, fn))
                    refresh_local()
                except Exception as e:
                    messagebox.showerror("错误", str(e), parent=self)

        tk.Button(btn_row, text="删除选中", command=delete_local,
                  bg="#e74c3c", fg="white", relief="flat", padx=12, cursor="hand2",
                  font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)

    def _on_tab_changed(self, event=None):
        """Notebook 标签页切换事件处理 -- 切换到备份恢复页时自动刷新远端文件列表。

        监听 ttk.Notebook 的 <<NotebookTabChanged>> 虚拟事件。
        当用户从"服务器配置"标签页切换到"备份 & 恢复"标签页（索引 1）时，
        自动调用 _refresh_file_list() 从 WebDAV 服务器获取最新的备份文件列表。

        Args:
            event: Tkinter 的 NotebookTabChanged 事件对象（可为 None，供手动调用）
        """
        try:
            nb = event.widget
            if nb.index(nb.select()) == 1:  # 切换到备份恢复标签页
                self._refresh_file_list()
        except Exception:
            pass

    # =========================================================================
    # 配置标签页
    # =========================================================================

    def _build_config_tab(self):
        """构建服务器配置标签页的完整内容。

        包含四个输入字段和一个按钮行：
          1. WebDAV 服务器地址（文本输入）
          2. 用户名（文本输入）
          3. 密码（掩码输入，show="*" 隐藏明文）
          4. 远程备份路径（文本输入）
          5. 测试连接按钮 + 保存配置按钮
          6. 连接状态提示标签（初始为空）
        """
        f = self._config_frame                                 # 简写引用
        # 统一边距参数（水平、上边距、下边距）
        px, py_top, py_btm = 15, (15, 2), (2, 8)
        font_label = (Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL)  # 标签字体

        # 1. 服务器地址
        tk.Label(f, text="WebDAV 服务器地址", bg="#ffffff", font=font_label,
                 ).pack(anchor="w", padx=px, pady=py_top)
        self._url_var = tk.StringVar()                         # 服务器地址的 StringVar
        _, url_outer = bordered_entry(f, textvariable=self._url_var)
        url_outer.pack(fill=tk.X, padx=px, pady=py_btm)

        # 2. 用户名
        tk.Label(f, text="用户名", bg="#ffffff", font=font_label,
                 ).pack(anchor="w", padx=px, pady=py_top)
        self._user_var = tk.StringVar()                        # 用户名的 StringVar
        _, user_outer = bordered_entry(f, textvariable=self._user_var)
        user_outer.pack(fill=tk.X, padx=px, pady=py_btm)

        # 3. 密码（show="*" 隐藏输入内容）
        tk.Label(f, text="密码", bg="#ffffff", font=font_label,
                 ).pack(anchor="w", padx=px, pady=py_top)
        self._pass_var = tk.StringVar()                        # 密码的 StringVar
        _, pass_outer = bordered_entry(f, textvariable=self._pass_var, show="*")  # 掩码显示
        pass_outer.pack(fill=tk.X, padx=px, pady=py_btm)

        # 4. 远程备份路径
        tk.Label(f, text="远程备份路径", bg="#ffffff", font=font_label,
                 ).pack(anchor="w", padx=px, pady=py_top)
        self._path_var = tk.StringVar()                        # 远程路径的 StringVar
        _, path_outer = bordered_entry(f, textvariable=self._path_var)
        path_outer.pack(fill=tk.X, padx=px, pady=(2, 12))     # 底边距稍大

        # 5. 测试连接 + 保存配置按钮行
        btn_row = tk.Frame(f, bg="#ffffff")
        btn_row.pack(fill=tk.X, padx=px)
        # "测试连接" -- 绿色背景，先保存配置再测试
        tk.Button(btn_row, text="测试连接", command=self._test_connection,
                  bg="#27ae60", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=14, pady=5,
                  activebackground="#219a52", activeforeground="white",
                  ).pack(side=tk.LEFT)
        # "保存配置" -- 蓝色背景，持久化当前表单中的配置
        tk.Button(btn_row, text="保存配置", command=self._save_config,
                  bg="#3498db", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=14, pady=5,
                  activebackground="#2980b9", activeforeground="white",
                  ).pack(side=tk.LEFT, padx=(8, 0))

        # 6. 连接状态提示标签（初始为空文本）
        self._conn_status = tk.Label(f, text="", bg="#ffffff", fg="#7f8c8d",
                                     font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL))
        self._conn_status.pack(anchor="w", padx=px, pady=(8, 0))

    def _load_config(self):
        """将已保存的 WebDAV 配置加载到表单字段中。

        从 self._cfg（WebDAVConfig 对象）读取各字段值并填入对应的输入框。
        """
        self._url_var.set(self._cfg.url)                       # 填充服务器地址
        self._user_var.set(self._cfg.username)                 # 填充用户名
        self._pass_var.set(self._cfg.password)                 # 填充密码
        self._path_var.set(self._cfg.remote_path)              # 填充远程备份路径

    def _save_config(self):
        """保存配置：从表单读取值，写入 WebDAVConfig 并持久化到文件。

        保存步骤：
          1. 从各输入框读取值。
          2. 确保 URL 和远程路径以 / 结尾。
          3. 更新 _cfg 对象并调用 save() 持久化。
          4. 用新配置重建 BackupService 实例。
          5. 更新状态标签并尝试刷新远端文件列表。
        """
        url = self._url_var.get().strip()                      # 读取服务器地址
        if url and not url.endswith("/"):
            url += "/"                                         # 确保 URL 以 / 结尾
        path = self._path_var.get().strip() or "/dap_backup/"  # 读取远程路径，默认 /dap_backup/
        if path and not path.endswith("/"):
            path += "/"                                        # 确保路径以 / 结尾

        # 更新配置对象
        self._cfg.url = url
        self._cfg.username = self._user_var.get().strip()
        self._cfg.password = self._pass_var.get()              # 密码不去首尾空格
        self._cfg.remote_path = path
        self._cfg.save()                                       # 持久化保存到配置文件

        self._svc = BackupService(self._cfg)                   # 用新配置重建备份服务
        self._conn_status.configure(text="配置已保存", fg="#27ae60")  # 显示成功提示
        self._refresh_file_list()                              # 尝试刷新远端文件列表

    def _test_connection(self):
        """测试 WebDAV 服务器连接是否正常。

        先保存当前表单配置，然后调用 BackupService.test_connection()。
        测试结果以绿色（成功）或红色（失败）显示在状态标签中。
        """
        self._save_config()                                    # 先保存配置
        self._conn_status.configure(text="正在测试连接...", fg="#7f8c8d")  # 显示测试中提示
        self.update()                                          # 强制刷新 UI
        ok, msg = self._svc.test_connection()                  # 调用服务测试连接
        color = "#27ae60" if ok else "#e74c3c"                 # 成功绿色 / 失败红色
        self._conn_status.configure(text=msg, fg=color)        # 显示测试结果

    # =========================================================================
    # 备份恢复标签页
    # =========================================================================

    def _build_action_tab(self):
        """构建备份恢复标签页的完整内容。

        布局（从上到下）：
          1. 操作说明提示文字
          2. 立即备份按钮 + 状态标签
          3. 分隔线
          4. 远端备份文件列表标题
          5. 刷新列表按钮
          6. 文件列表 Treeview（文件名、修改时间，带水平和垂直滚动条）
          7. 操作按钮行（恢复选中、删除选中）
          8. 关闭按钮
        """
        f = self._action_frame                                 # 简写引用
        px = 15                                                # 统一水平边距

        # 1. 操作说明
        tk.Label(f, text="将当前数据备份到 WebDAV 服务器", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 fg="#2c3e50").pack(anchor="w", padx=px, pady=(15, 8))

        # 2. 立即备份按钮
        tk.Button(f, text="立即备份", command=self._do_backup,
                  bg="#27ae60", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=14, pady=5,
                  activebackground="#219a52", activeforeground="white",
                  ).pack(anchor="w", padx=15, pady=(0, 4))

        # 备份操作状态提示标签（初始为空）
        self._backup_status = tk.Label(f, text="", bg="#ffffff", fg="#7f8c8d",
                                       font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL))
        self._backup_status.pack(anchor="w", padx=15, pady=(0, 10))

        # 3. 分隔线
        tk.Frame(f, bg="#d0d5dd", height=1).pack(fill=tk.X, padx=15, pady=5)

        # 4. 远端文件列表标题
        tk.Label(f, text="远端备份文件", bg="#ffffff", fg="#2c3e50",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                 ).pack(anchor="w", padx=px, pady=(5, 8))

        # 5. 刷新列表按钮行
        btn_row = tk.Frame(f, bg="#ffffff")
        btn_row.pack(fill=tk.X, padx=15, pady=(0, 5))
        tk.Button(btn_row, text="刷新列表", command=self._refresh_file_list,
                  bg="#3498db", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=14, pady=5,
                  activebackground="#2980b9", activeforeground="white",
                  ).pack(side=tk.LEFT)

        # 6. 文件列表 Treeview（表格形式展示备份文件）
        tree_frame = tk.Frame(f, bg="#ffffff")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 5))

        # 定义两列：文件名 + 修改时间
        columns = ("name", "modified")
        self._file_tree = ttk.Treeview(tree_frame, columns=columns,
                                       show="headings", height=6,    # 6 行可见高度
                                       selectmode="browse")          # 单选模式
        self._file_tree.heading("name", text="文件名", anchor="w")
        self._file_tree.heading("modified", text="修改时间", anchor="w")
        self._file_tree.column("name", width=320, anchor="w", stretch=False)       # 文件名列宽320
        self._file_tree.column("modified", width=180, anchor="w", stretch=False)    # 时间列宽180

        # 使用 grid 布局确保滚动条精准对齐 Treeview
        tree_frame.grid_rowconfigure(0, weight=1)              # 行 0 可扩展
        tree_frame.grid_columnconfigure(0, weight=1)           # 列 0 可扩展

        # 垂直滚动条
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                    command=self._file_tree.yview)
        # 水平滚动条（文件名过长时使用）
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL,
                                    command=self._file_tree.xview)
        self._file_tree.configure(yscrollcommand=scrollbar_y.set,
                                  xscrollcommand=scrollbar_x.set)  # 双向绑定

        # Grid 布局：Treeview 主格 (0,0)，垂直滚动条 (0,1)，水平滚动条 (1,0) 跨两列
        self._file_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew", columnspan=2)

        # 7. 操作按钮行（恢复 + 删除）
        op_row = tk.Frame(f, bg="#ffffff")
        op_row.pack(fill=tk.X, padx=15, pady=(0, 15))

        # "恢复选中" -- 蓝底白字，下载选中的远端备份文件并覆盖本地数据
        tk.Button(op_row, text="恢复选中", command=self._do_restore,
                  bg="#3498db", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=14, pady=5,
                  activebackground="#2980b9", activeforeground="white",
                  ).pack(side=tk.LEFT, padx=(0, 8))

        # "删除选中" -- 红底白字，删除选中的远端备份文件
        tk.Button(op_row, text="删除选中", command=self._do_delete_backup,
                  bg="#e74c3c", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=14, pady=5,
                  activebackground="#c0392b", activeforeground="white",
                  ).pack(side=tk.LEFT)

        # 8. 关闭按钮
        tk.Button(f, text="关闭", command=self.destroy,
                  bg="#ecf0f1", fg="#2c3e50", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                  relief="flat", padx=20, pady=6,
                  ).pack(pady=(0, 10))

    # =========================================================================
    # 备份 / 恢复 / 删除操作
    # =========================================================================

    def _refresh_file_list(self):
        """刷新远端备份文件列表。

        调用 BackupService.list_backups() 获取远端所有备份文件信息，
        清空 Treeview 并重新填充。文件名按字母倒序排列（最新的通常在前）。
        """
        # 清空 Treeview 中所有现有行
        for item in self._file_tree.get_children():
            self._file_tree.delete(item)

        ok, msg, files = self._svc.list_backups()              # 获取远端文件列表
        if ok:
            # 按文件名字母倒序排列（通常最新备份包含时间戳，故靠前）
            files.sort(key=lambda x: x["name"], reverse=True)
            for f in files:
                # 以文件路径作为行标识符(iid)，方便后续通过选中行定位文件
                self._file_tree.insert("", tk.END, iid=f["path"],
                                       values=(f["name"], f["modified"]))
        else:
            # 获取失败时在状态标签中显示错误信息
            self._backup_status.configure(text=f"获取列表失败: {msg}", fg="#e74c3c")

    def _do_backup(self):
        """执行本地数据备份到 WebDAV 服务器的操作。

        调用 BackupService.backup() 上传本地数据文件到远端。
        操作进度和结果显示在 backup_status 标签中。
        备份成功时自动刷新远端文件列表。
        """
        self._backup_status.configure(text="正在备份...", fg="#7f8c8d")  # 显示进度提示
        self.update()                                          # 强制刷新 UI
        ok, msg = self._svc.backup(self._data_file)            # 调用服务执行备份上传
        color = "#27ae60" if ok else "#e74c3c"                 # 成功绿色 / 失败红色
        self._backup_status.configure(text=msg, fg=color)      # 显示结果
        if ok:
            self._refresh_file_list()                          # 成功后自动刷新文件列表

    def _do_restore(self):
        """从远端备份文件恢复本地数据。

        操作步骤：
          1. 获取 Treeview 中选中的远端文件。
          2. 弹出二次确认对话框（警告会覆盖当前数据）。
          3. 下载远端备份文件内容。
          4. 验证下载内容是否为合法 JSON 格式。
          5. 写入本地数据文件。
          6. 调用 on_restore 回调通知 MainWindow 重新加载数据。
          7. 弹出成功提示。
        """
        sel = self._file_tree.selection()                      # 获取当前选中行
        if not sel:
            messagebox.showinfo("提示", "请先选择要恢复的备份文件", parent=self)
            return

        # 从选中行获取文件名，用于确认提示
        fname = self._file_tree.item(sel[0], "values")[0]

        # 二次确认（警告用户当前数据将被覆盖）
        if not messagebox.askyesno("确认恢复",
                                   f"确定要用\u300c{fname}\u300d覆盖当前数据吗？\n\n"
                                   "当前数据将丢失！", parent=self):
            return

        # 下载备份内容
        ok, msg, body = self._svc.restore(sel[0])              # sel[0] 是远端文件路径（iid）
        if ok:
            # 写入文件前验证 JSON 格式有效性
            try:
                json.loads(body.decode("utf-8"))               # 尝试解析 JSON 以检查格式
            except (json.JSONDecodeError, UnicodeDecodeError):
                messagebox.showerror("错误", "备份文件格式错误", parent=self)
                return

            # 将下载的备份数据写入本地数据文件（二进制写入）
            with open(self._data_file, "wb") as f:
                f.write(body)

            # 通知主窗口重新加载数据并刷新界面
            if self.on_restore:
                self.on_restore()

            messagebox.showinfo("成功", f"数据已从\u300c{fname}\u300d恢复并自动刷新。",
                                parent=self)
        else:
            messagebox.showerror("恢复失败", msg, parent=self)

    def _do_delete_backup(self):
        """删除远端服务器上的备份文件。

        获取 Treeview 选中行，弹出确认对话框，调用 BackupService 执行删除。
        删除成功后自动刷新文件列表。
        """
        sel = self._file_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择要删除的备份", parent=self)
            return

        fname = self._file_tree.item(sel[0], "values")[0]     # 获取文件名用于确认
        if messagebox.askyesno("确认删除", f"确定要删除远端备份\u300c{fname}\u300d吗？", parent=self):
            ok, msg = self._svc.delete_backup(sel[0])          # 调用服务删除远端文件
            if ok:
                self._refresh_file_list()                      # 删除成功后刷新列表
            else:
                messagebox.showerror("删除失败", msg, parent=self)

    # =========================================================================
    # 窗口居中
    # =========================================================================



