"""
WebDAV 备份对话框 - 配置服务器连接、执行备份和恢复操作

功能：
- 服务器配置（地址、用户名、密码、远程路径）
- 测试WebDAV连接
- 数据备份到远端服务器
- 远端备份文件列表查看
- 从远端恢复数据
- 删除远端备份文件
"""

import tkinter as tk  # 导入Tkinter GUI库，用于构建桌面应用界面组件
from tkinter import ttk, messagebox  # ttk提供增强组件(Notebook等)，messagebox弹窗
from utils.config import Config  # 导入Config配置类，获取字体等UI配置常量
from utils.webdav_config import WebDAVConfig  # 导入WebDAV配置管理类（加载/保存服务器设置）
from utils.helpers import bordered_entry  # 导入辅助函数：创建带边框样式的输入框
from services.backup_service import BackupService  # 导入备份服务类（处理WebDAV的备份/恢复操作）


class BackupDialog(tk.Toplevel):
    """WebDAV 备份管理对话框 - 继承自tk.Toplevel

    使用Notebook标签页组织界面：
    - 标签页1：服务器配置（地址、用户名、密码、远程路径、测试连接）
    - 标签页2：备份恢复（备份按钮、远端文件列表、恢复/删除）
    """

    def __init__(self, parent, data_file_path: str):
        """初始化备份对话框

        Args:
            parent: 父级窗口
            data_file_path: 本地数据文件的路径（用于备份上传和恢复下载）
        """
        super().__init__(parent)
        self.title("WebDAV 备份管理")  # 窗口标题
        self._data_file = data_file_path  # 保存数据文件路径
        self._cfg = WebDAVConfig.load()  # 加载已保存的WebDAV配置
        self._svc = BackupService(self._cfg)  # 使用配置创建备份服务实例

        self._setup_window()  # 配置窗口属性
        self._build_ui()  # 构建标签页UI
        self._load_config()  # 加载配置到表单
        self._center_window()  # 窗口居中
        self.grab_set()  # 设置为模态窗口

    def _setup_window(self):
        """配置窗口属性"""
        self.geometry("560x550")  # 初始大小
        self.minsize(480, 420)  # 最小尺寸
        self.resizable(True, True)  # 允许调整大小
        self.configure(bg="#ffffff")  # 白色背景

    def _build_ui(self):
        """构建标签页UI（可滚动）
        使用Canvas+Scrollbar包裹Notebook，防止窗口过小时内容溢出
        """
        # 可滚动画布
        canvas = tk.Canvas(self, bg="#ffffff", highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Notebook 放入 Canvas
        nb = ttk.Notebook(canvas)
        canvas.create_window((0, 0), window=nb, anchor="nw", tags="nb_win")

        # 页面大小变化时更新滚动区域和窗口宽度
        def _on_nb_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig("nb_win", width=canvas.winfo_width() - 4)
        nb.bind("<Configure>", _on_nb_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("nb_win", width=e.width - 4))

        # 鼠标滚轮滚动
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta/120), "units"))

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        # ---- 标签页1：服务器配置 ----
        self._config_frame = tk.Frame(nb, bg="#ffffff")
        nb.add(self._config_frame, text="  服务器配置  ")
        self._build_config_tab()

        # ---- 标签页2：备份恢复 ----
        self._action_frame = tk.Frame(nb, bg="#ffffff")
        nb.add(self._action_frame, text="  备份 & 恢复  ")
        self._build_action_tab()

    # ==================== 配置标签页 ====================

    def _build_config_tab(self):
        """构建服务器配置标签页的内容

        包含：服务器地址、用户名、密码、远程路径的输入框，
        以及测试连接和保存配置按钮。
        """
        f = self._config_frame  # 简写引用
        px, py_top, py_btm = 15, (15, 2), (2, 8)  # 统一边距参数
        font_label = (Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL)  # 标签字体

        # 服务器地址输入
        tk.Label(f, text="WebDAV 服务器地址", bg="#ffffff", font=font_label,
                 ).pack(anchor="w", padx=px, pady=py_top)  # 标签
        self._url_var = tk.StringVar()  # 服务器地址的StringVar
        _, url_outer = bordered_entry(f, textvariable=self._url_var)  # 带边框输入框
        url_outer.pack(fill=tk.X, padx=px, pady=py_btm)  # 水平填充

        # 用户名输入
        tk.Label(f, text="用户名", bg="#ffffff", font=font_label,
                 ).pack(anchor="w", padx=px, pady=py_top)
        self._user_var = tk.StringVar()  # 用户名的StringVar
        _, user_outer = bordered_entry(f, textvariable=self._user_var)
        user_outer.pack(fill=tk.X, padx=px, pady=py_btm)

        # 密码输入 - 使用show="*"隐藏密码显示
        tk.Label(f, text="密码", bg="#ffffff", font=font_label,
                 ).pack(anchor="w", padx=px, pady=py_top)
        self._pass_var = tk.StringVar()  # 密码的StringVar
        _, pass_outer = bordered_entry(f, textvariable=self._pass_var, show="*")  # show="*" 密码掩码
        pass_outer.pack(fill=tk.X, padx=px, pady=py_btm)

        # 远程备份路径输入
        tk.Label(f, text="远程备份路径", bg="#ffffff", font=font_label,
                 ).pack(anchor="w", padx=px, pady=py_top)
        self._path_var = tk.StringVar()  # 远程路径的StringVar
        _, path_outer = bordered_entry(f, textvariable=self._path_var)
        path_outer.pack(fill=tk.X, padx=px, pady=(2, 12))  # 下方间距稍大

        # 测试连接 + 保存配置按钮行
        btn_row = tk.Frame(f, bg="#ffffff")
        btn_row.pack(fill=tk.X, padx=px)
        # 测试连接按钮 - 绿底白字
        tk.Button(btn_row, text="测试连接", command=self._test_connection,
                  bg="#27ae60", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=14, pady=5,
                  activebackground="#219a52", activeforeground="white",
                  ).pack(side=tk.LEFT)
        # 保存配置按钮 - 蓝底白字
        tk.Button(btn_row, text="保存配置", command=self._save_config,
                  bg="#3498db", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=14, pady=5,
                  activebackground="#2980b9", activeforeground="white",
                  ).pack(side=tk.LEFT, padx=(8, 0))

        # 连接状态提示标签
        self._conn_status = tk.Label(f, text="", bg="#ffffff", fg="#7f8c8d",
                                     font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL))
        self._conn_status.pack(anchor="w", padx=px, pady=(8, 0))

    def _load_config(self):
        """将已保存的WebDAV配置加载到表单字段"""
        self._url_var.set(self._cfg.url)  # 填充服务器地址
        self._user_var.set(self._cfg.username)  # 填充用户名
        self._pass_var.set(self._cfg.password)  # 填充密码
        self._path_var.set(self._cfg.remote_path)  # 填充远程路径

    def _save_config(self):
        """保存配置：从表单读取值，写入WebDAVConfig并持久化到文件

        保存后重新创建BackupService实例以使用新配置，
        并尝试刷新远端文件列表。
        """
        url = self._url_var.get().strip()  # 读取服务器地址
        if url and not url.endswith("/"):
            url += "/"  # 确保以 / 结尾
        path = self._path_var.get().strip() or "/dap_backup/"  # 读取远程路径
        if path and not path.endswith("/"):
            path += "/"  # 确保以 / 结尾

        self._cfg.url = url
        self._cfg.username = self._user_var.get().strip()
        self._cfg.password = self._pass_var.get()  # 不strip密码
        self._cfg.remote_path = path
        self._cfg.save()  # 持久化保存到配置文件
        self._svc = BackupService(self._cfg)  # 用新配置重建服务实例
        self._conn_status.configure(text="配置已保存", fg="#27ae60")
        self._refresh_file_list()  # 尝试刷新远端文件列表

    def _test_connection(self):
        """测试WebDAV服务器连接

        先保存当前配置，然后调用BackupService测试连接。
        测试结果显示在状态标签中（绿色成功/红色失败）。
        """
        self._save_config()  # 先保存配置
        self._conn_status.configure(text="正在测试连接...", fg="#7f8c8d")  # 显示测试中
        self.update()  # 强制刷新UI显示
        ok, msg = self._svc.test_connection()  # 调用服务测试连接
        color = "#27ae60" if ok else "#e74c3c"  # 成功绿色，失败红色
        self._conn_status.configure(text=msg, fg=color)  # 显示结果

    # ==================== 备份恢复标签页 ====================

    def _build_action_tab(self):
        """构建备份恢复标签页的内容

        包含：备份按钮、远端文件列表（Treeview）、恢复/删除按钮。
        """
        f = self._action_frame  # 简写引用
        px = 15  # 水平边距

        # 备份操作说明
        tk.Label(f, text="将当前数据备份到 WebDAV 服务器", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 fg="#2c3e50").pack(anchor="w", padx=px, pady=(15, 8))

        # 立即备份按钮 - 绿底白字
        tk.Button(f, text="立即备份", command=self._do_backup,
                  bg="#27ae60", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=14, pady=5,
                  activebackground="#219a52", activeforeground="white",
                  ).pack(anchor="w", padx=15, pady=(0, 4))

        # 备份操作状态提示
        self._backup_status = tk.Label(f, text="", bg="#ffffff", fg="#7f8c8d",
                                       font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL))
        self._backup_status.pack(anchor="w", padx=15, pady=(0, 10))

        # 分隔线
        tk.Frame(f, bg="#d0d5dd", height=1).pack(fill=tk.X, padx=15, pady=5)

        # 远端文件列表标题
        tk.Label(f, text="远端备份文件", bg="#ffffff", fg="#2c3e50",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                 ).pack(anchor="w", padx=px, pady=(5, 8))

        # 刷新列表按钮行
        btn_row = tk.Frame(f, bg="#ffffff")
        btn_row.pack(fill=tk.X, padx=15, pady=(0, 5))
        tk.Button(btn_row, text="刷新列表", command=self._refresh_file_list,
                  bg="#3498db", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=14, pady=5,
                  activebackground="#2980b9", activeforeground="white",
                  ).pack(side=tk.LEFT)  # 左侧放置

        # Treeview文件列表 - 显示远端备份文件
        tree_frame = tk.Frame(f, bg="#ffffff")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 5))

        columns = ("name", "modified")  # 文件名 + 修改时间两列
        self._file_tree = ttk.Treeview(tree_frame, columns=columns,
                                       show="headings", height=6,  # 6行可见高度
                                       selectmode="browse")  # 单选
        self._file_tree.heading("name", text="文件名", anchor="w")
        self._file_tree.heading("modified", text="修改时间", anchor="w")
        self._file_tree.column("name", width=320, anchor="w", stretch=False)  # 文件名列宽320
        self._file_tree.column("modified", width=180, anchor="w", stretch=False)  # 时间列宽180

        # 使用 grid 布局确保滚动条精准定位
        tree_frame.grid_rowconfigure(0, weight=1)  # tree 行可扩展
        tree_frame.grid_columnconfigure(0, weight=1)  # tree 列可扩展

        # 垂直滚动条
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                    command=self._file_tree.yview)
        # 水平滚动条
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL,
                                    command=self._file_tree.xview)
        self._file_tree.configure(yscrollcommand=scrollbar_y.set,
                                  xscrollcommand=scrollbar_x.set)
        # 布局：Tree(0,0) | VScroll(0,1), HScroll(1,0) 横跨两列
        self._file_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew", columnspan=2)

        # 操作按钮行（恢复/删除）
        op_row = tk.Frame(f, bg="#ffffff")
        op_row.pack(fill=tk.X, padx=15, pady=(0, 15))

        # 恢复选中按钮 - 蓝底白字
        tk.Button(op_row, text="恢复选中", command=self._do_restore,
                  bg="#3498db", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=14, pady=5,
                  activebackground="#2980b9", activeforeground="white",
                  ).pack(side=tk.LEFT, padx=(0, 8))

        # 删除选中按钮 - 红底白字
        tk.Button(op_row, text="删除选中", command=self._do_delete_backup,
                  bg="#e74c3c", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=14, pady=5,
                  activebackground="#c0392b", activeforeground="white",
                  ).pack(side=tk.LEFT)

        # 关闭按钮 - 灰色底深色字
        tk.Button(f, text="关闭", command=self.destroy,
                  bg="#ecf0f1", fg="#2c3e50", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                  relief="flat", padx=20, pady=6,
                  ).pack(pady=(0, 10))

    # ==================== 操作 ====================

    def _refresh_file_list(self):
        """刷新远端备份文件列表

        调用BackupService获取远端文件列表，清空Treeview后重新填充。
        文件名按字母倒序排列（最新的备份通常在最前面）。
        """
        for item in self._file_tree.get_children():
            self._file_tree.delete(item)  # 清空现有行

        ok, msg, files = self._svc.list_backups()  # 获取远端文件列表
        if ok:
            files.sort(key=lambda x: x["name"], reverse=True)  # 按文件名倒序排列
            for f in files:
                # 插入文件行，以文件路径作为行ID（iid）
                self._file_tree.insert("", tk.END, iid=f["path"],
                                       values=(f["name"], f["modified"]))
        else:
            self._backup_status.configure(text=f"获取列表失败: {msg}", fg="#e74c3c")  # 显示错误

    def _do_backup(self):
        """执行备份操作

        将本地数据文件上传到WebDAV服务器，显示进度和结果状态。
        备份成功后自动刷新远端文件列表。
        """
        self._backup_status.configure(text="正在备份...", fg="#7f8c8d")  # 显示进度
        self.update()  # 强制刷新UI
        ok, msg = self._svc.backup(self._data_file)  # 调用服务执行备份
        color = "#27ae60" if ok else "#e74c3c"  # 成功绿/失败红
        self._backup_status.configure(text=msg, fg=color)  # 显示结果
        if ok:
            self._refresh_file_list()  # 成功后刷新文件列表

    def _do_restore(self):
        """从远端恢复数据

        让用户选择远端备份文件，确认后下载并覆盖本地数据文件。
        恢复前进行JSON格式验证，恢复后提示用户重启程序。
        """
        sel = self._file_tree.selection()  # 获取选中行
        if not sel:
            messagebox.showinfo("提示", "请先选择要恢复的备份文件", parent=self)
            return

        fname = self._file_tree.item(sel[0], "values")[0]  # 获取选中的文件名
        # 二次确认（数据覆盖警告）
        if not messagebox.askyesno("确认恢复",
                                   f"确定要用\u300c{fname}\u300d覆盖当前数据吗？\n\n"
                                   "当前数据将丢失！", parent=self):
            return

        ok, msg, body = self._svc.restore(sel[0])  # 调用服务下载备份内容
        if ok:
            # 在写入文件前验证JSON格式的有效性
            try:
                json.loads(body.decode("utf-8"))  # 尝试解析JSON判断格式
            except (json.JSONDecodeError, UnicodeDecodeError):
                messagebox.showerror("错误", "备份文件格式错误", parent=self)
                return

            # 将下载的备份数据写入本地文件
            with open(self._data_file, "wb") as f:
                f.write(body)
            messagebox.showinfo("成功", f"数据已从\u300c{fname}\u300d恢复，\n请重新启动程序以加载新数据。",
                                parent=self)
        else:
            messagebox.showerror("恢复失败", msg, parent=self)

    def _do_delete_backup(self):
        """删除远端备份文件

        选择远端文件进行删除操作，删除后刷新文件列表。
        """
        sel = self._file_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择要删除的备份", parent=self)
            return

        fname = self._file_tree.item(sel[0], "values")[0]  # 获取文件名用于确认提示
        if messagebox.askyesno("确认删除", f"确定要删除远端备份\u300c{fname}\u300d吗？", parent=self):
            ok, msg = self._svc.delete_backup(sel[0])  # 调用服务删除远端文件
            if ok:
                self._refresh_file_list()  # 删除成功后刷新列表
            else:
                messagebox.showerror("删除失败", msg, parent=self)

    def _center_window(self):
        """窗口居中显示"""
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        pw = self.master.winfo_width()
        ph = self.master.winfo_height()
        px = self.master.winfo_rootx()
        py = self.master.winfo_rooty()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")
