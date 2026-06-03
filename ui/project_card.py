"""
项目卡片组件 - 在看板列中以卡片形式展示单个项目

每个卡片显示项目名称、截止日期和状态颜色标识，
支持点击选中、双击编辑、左右箭头移动阶段、详情/编辑按钮
"""

import tkinter as tk  # 导入Tkinter GUI库，用于构建桌面应用界面组件
from datetime import date  # 导入date类，用于截止日期的计算和比较
from models.project import Project  # 导入Project模型类，表示一个等保测评项目实体
from utils.config import Config  # 导入Config配置类，获取颜色、字体等UI配置常量


class _ToolTip:
    """简易按钮悬浮提示"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tw = None
        widget.bind("<Enter>", self._enter)
        widget.bind("<Leave>", self._leave)

    def _enter(self, event=None):
        x, y = self.widget.winfo_rootx() + 5, self.widget.winfo_rooty() + 22
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tw, text=self.text, bg="#333", fg="white",
                         font=("Microsoft YaHei", 8), padx=4, pady=1)
        label.pack()

    def _leave(self, event=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None


def _add_tooltip(widget, text):
    _ToolTip(widget, text)


def _show_report_dialog(parent, cname="", sname="", location="", deadline=""):
    """报告打印编辑确认对话框"""
    from tkinter import messagebox
    dlg = tk.Toplevel(parent)
    dlg.title("报告打印信息确认")
    dlg.geometry("520x680")
    dlg.minsize(440, 500)
    dlg.configure(bg="#ffffff")
    dlg.grab_set()
    dlg.resizable(True, True)

    result = {"confirmed": False}

    import json, os
    from utils.config import Config
    from utils.helpers import bordered_entry
    defaults = {}
    def_path = os.path.join(Config.get_data_dir(), "data", "report_defaults.json")
    if os.path.exists(def_path):
        try:
            with open(def_path, "r", encoding="utf-8") as f:
                defaults = json.load(f)
        except Exception:
            pass

    # ---- 可滚动内容区域 ----
    canvas = tk.Canvas(dlg, bg="#ffffff", highlightthickness=0)
    scrollbar = tk.Scrollbar(dlg, orient=tk.VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    main = tk.Frame(canvas, bg="#ffffff", padx=20, pady=15)
    cw = canvas.create_window((0, 0), window=main, anchor="nw")
    main.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
    canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta/120), "units"))
    dlg.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta/120), "units"))

    def _make_row(label, default=""):
        tk.Label(main, text=label, bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL)).pack(anchor="w")
        var = tk.StringVar(value=default)
        _, outer = bordered_entry(main, textvariable=var)
        outer.pack(fill=tk.X, pady=(2, 6))
        return var

    tk.Label(main, text="报告打印信息确认", bg="#ffffff", fg="#2c3e50",
             font=(Config.FONT_FAMILY, Config.FONT_SIZE_HEADER, "bold"),
             ).pack(anchor="w", pady=(0, 10))

    v_cname = _make_row("客户公司全称", defaults.get("cname", cname))
    v_contract = _make_row("合同编号或项目名称", defaults.get("contract", f"{cname}网络安全等级保护测评服务项目"))
    v_location = _make_row("所属地", defaults.get("location", location))
    v_sname = _make_row("系统名称", defaults.get("sname", sname))
    v_crm = _make_row("是否录入CRM", defaults.get("crm", "是"))
    v_deadline = _make_row("编制/审核/批准日期", defaults.get("deadline", deadline))
    v_author = _make_row("编制人", defaults.get("author", ""))
    v_reviewer = _make_row("审核人", defaults.get("reviewer", ""))
    v_pentester = _make_row("渗透人员", defaults.get("pentester", ""))
    v_conclusion = _make_row("测评结论及重大风险隐患数量", defaults.get("conclusion", ""))
    v_seal = _make_row("盖章", defaults.get("seal", ""))
    v_print_req = _make_row("打印要求", defaults.get("print_req", ""))
    v_leader = _make_row("项目组长联系人", defaults.get("leader", ""))
    v_actual = _make_row("实际报告编制人", defaults.get("actual_author", ""))

    def _collect():
        return {
            "cname": v_cname.get().strip(),
            "contract": v_contract.get().strip(),
            "location": v_location.get().strip(),
            "sname": v_sname.get().strip(),
            "crm": v_crm.get().strip(),
            "deadline": v_deadline.get().strip(),
            "author": v_author.get().strip(),
            "reviewer": v_reviewer.get().strip(),
            "pentester": v_pentester.get().strip(),
            "conclusion": v_conclusion.get().strip(),
            "seal": v_seal.get().strip(),
            "print_req": v_print_req.get().strip(),
            "leader": v_leader.get().strip(),
            "actual_author": v_actual.get().strip(),
        }

    def _on_confirm():
        result["confirmed"] = True
        result["data"] = _collect()
        dlg.destroy()

    def _open_defaults_editor():
        """打开设置默认值的独立编辑框"""
        import json, os
        from utils.config import Config
        path = os.path.join(Config.get_data_dir(), "data", "report_defaults.json")
        saved = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
            except Exception:
                pass
        # 如果无保存值，用当前对话框数据填充
        if not any(saved.values()):
            saved = _collect()

        dedit = tk.Toplevel(dlg)
        dedit.title("设置默认值")
        dedit.geometry("500x600")
        dedit.minsize(420, 400)
        dedit.configure(bg="#ffffff")
        dedit.grab_set()

        dcanvas = tk.Canvas(dedit, bg="#ffffff", highlightthickness=0)
        dscroll = tk.Scrollbar(dedit, orient=tk.VERTICAL, command=dcanvas.yview)
        dcanvas.configure(yscrollcommand=dscroll.set)
        dscroll.pack(side=tk.RIGHT, fill=tk.Y)
        dcanvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        dmain = tk.Frame(dcanvas, bg="#ffffff", padx=20, pady=15)
        dw = dcanvas.create_window((0, 0), window=dmain, anchor="nw")
        dmain.bind("<Configure>", lambda e: dcanvas.configure(scrollregion=dcanvas.bbox("all")))
        dcanvas.bind("<Configure>", lambda e: dcanvas.itemconfig(dw, width=e.width))
        dcanvas.bind("<MouseWheel>", lambda e: dcanvas.yview_scroll(int(-e.delta/120), "units"))
        dedit.bind("<MouseWheel>", lambda e: dcanvas.yview_scroll(int(-e.delta/120), "units"))

        dvars = {}
        for label, key in [
            ("客户公司全称", "cname"), ("合同编号或项目名称", "contract"),
            ("所属地", "location"), ("系统名称", "sname"), ("是否录入CRM", "crm"),
            ("编制/审核/批准日期", "deadline"), ("编制人", "author"),
            ("审核人", "reviewer"), ("渗透人员", "pentester"),
            ("测评结论及重大风险隐患数量", "conclusion"), ("盖章", "seal"),
            ("打印要求", "print_req"), ("项目组长联系人", "leader"),
            ("实际报告编制人", "actual_author"),
        ]:
            tk.Label(dmain, text=label, bg="#ffffff",
                     font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL)).pack(anchor="w")
            var = tk.StringVar(value=saved.get(key, ""))
            from utils.helpers import bordered_entry
            _, outer = bordered_entry(dmain, textvariable=var, width=40)
            outer.pack(fill=tk.X, pady=(2, 5))
            dvars[key] = var

        def _save_and_close():
            data = {k: v.get().strip() for k, v in dvars.items()}
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # 回填到主对话框
            for key, var in dvars.items():
                target = {
                    "cname": v_cname, "contract": v_contract, "location": v_location,
                    "sname": v_sname, "crm": v_crm, "deadline": v_deadline,
                    "author": v_author, "reviewer": v_reviewer, "pentester": v_pentester,
                    "conclusion": v_conclusion, "seal": v_seal,
                    "print_req": v_print_req, "leader": v_leader,
                    "actual_author": v_actual,
                }.get(key)
                if target:
                    target.set(data[key])
            messagebox.showinfo("提示", "默认值已保存", parent=dedit)
            dedit.destroy()

        # 底部按钮
        dbtn_frame = tk.Frame(dedit, bg="#f0f2f5")
        dbtn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Frame(dbtn_frame, bg="#d0d5dd", height=1).pack(fill=tk.X)
        dbtn_inner = tk.Frame(dbtn_frame, bg="#f0f2f5")
        dbtn_inner.pack(fill=tk.X, padx=16, pady=8)
        tk.Button(dbtn_inner, text="取消", command=dedit.destroy,
                  bg="#ffffff", fg="#2c3e50", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  relief="flat", padx=20, pady=5,
                  highlightbackground="#d0d5dd", highlightthickness=1,
                  ).pack(side=tk.RIGHT, padx=(10, 0))
        tk.Button(dbtn_inner, text="保存", command=_save_and_close,
                  bg="#3498db", fg="white", cursor="hand2",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                  relief="flat", padx=20, pady=5,
                  ).pack(side=tk.RIGHT)
        dedit.bind("<Return>", lambda e: _save_and_close())
        dedit.bind("<Escape>", lambda e: dedit.destroy())

    # 底部按钮（固定在对话框底部）
    btn_frame = tk.Frame(dlg, bg="#f0f2f5")
    btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
    tk.Frame(btn_frame, bg="#d0d5dd", height=1).pack(fill=tk.X)
    btn_inner = tk.Frame(btn_frame, bg="#f0f2f5")
    btn_inner.pack(fill=tk.X, padx=16, pady=8)
    tk.Button(btn_inner, text="设置默认值", command=_open_defaults_editor,
              bg="#f0f2f5", fg="#2c3e50", cursor="hand2",
              font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
              relief="flat", padx=12, pady=5,
              activebackground="#d5dbdb",
              ).pack(side=tk.LEFT)
    tk.Button(btn_inner, text="取消", command=dlg.destroy,
              bg="#ffffff", fg="#2c3e50", cursor="hand2",
              font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
              relief="flat", padx=20, pady=5,
              highlightbackground="#d0d5dd", highlightthickness=1,
              activebackground="#f0f2f5",
              ).pack(side=tk.RIGHT, padx=(10, 0))
    tk.Button(btn_inner, text="确认", command=_on_confirm,
              bg="#3498db", fg="white", cursor="hand2",
              font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
              relief="flat", padx=20, pady=5,
              activebackground="#2980b9",
              ).pack(side=tk.RIGHT)

    dlg.bind("<Return>", lambda e: _on_confirm())
    dlg.bind("<Escape>", lambda e: dlg.destroy())
    parent.wait_window(dlg)

    if result["confirmed"]:
        return result["data"]
    return None


class ProjectCard(tk.Frame):
    """项目卡片组件 - 继承自tk.Frame，作为看板列中的项目展示卡片

    展示项目摘要信息，支持多种交互：
    - 单击：选中卡片（高亮边框）
    - 双击：直接打开编辑对话框
    - 左/右箭头：快速移动项目到上/下一阶段
    - 详情按钮：打开项目详情窗口
    - 编辑按钮：打开项目编辑对话框

    Attributes:
        project: 关联的项目实体对象（Project实例）
        is_selected: 当前是否被选中（布尔值）
        on_click: 单击回调函数
        on_double_click: 双击回调函数（编辑）
        on_detail: 查看详情回调函数
        on_edit: 编辑回调函数
        on_move_prev: 移至上一阶段回调函数
        on_move_next: 移至下一阶段回调函数
    """

    def __init__(self, parent, project: Project, **kwargs):
        """初始化项目卡片组件

        Args:
            parent: 父级容器（通常为看板列内的卡片容器）
            project: 关联的项目实体对象
            **kwargs: 传递给父类tk.Frame的额外关键字参数
        """
        # 调用父类初始化，设置卡片背景色、边框颜色和鼠标手型光标
        super().__init__(parent, bg=Config.CARD_BG,
                         highlightbackground=Config.CARD_BORDER,
                         highlightthickness=1,
                         cursor="hand2", **kwargs)

        self.project = project  # 保存关联的项目实体对象引用
        self.is_selected = False  # 初始状态为未选中
        self.on_click = None  # 单击回调函数，由外部设置
        self.on_double_click = None  # 双击回调函数，由外部设置
        self.on_detail = None  # 查看详情回调函数，由外部设置
        self.on_edit = None  # 编辑回调函数，由外部设置
        self.on_copy = None  # 复制项目回调函数，由外部设置
        self.on_move_prev = None  # 左箭头移动回调函数，由外部设置
        self.on_move_next = None  # 右箭头移动回调函数，由外部设置

        self._build_ui()  # 构建卡片内部的UI组件布局
        self._bind_events()  # 绑定鼠标交互事件

    def _build_ui(self):
        """构建卡片布局：左侧颜色条 + 左箭头 | 居中内容 | 右箭头

        卡片整体使用水平布局（左右排列），内容区域包含公司名称、
        系统名称、备案号、截止日期等信息，垂直排列居中显示。
        """
        status_color = self._get_status_color()  # 根据截止日期计算状态颜色（绿/橙/红/灰）

        # ---- 左侧颜色条 ----
        # 4像素宽的垂直色条，用于直观展示项目紧急程度
        self._color_bar = tk.Frame(self, bg=status_color, width=4)
        self._color_bar.pack(side=tk.LEFT, fill=tk.Y)  # 左侧垂直填充
        self._color_bar.pack_propagate(False)  # 禁止子组件影响Frame尺寸（保持4px宽度）

        # ---- 左箭头按钮 ----
        # Unicode \u25c0 为 ◀ 字符，点击可将项目移至上一阶段
        self._prev_btn = tk.Button(
            self, text="\u25c0", command=self._on_prev_click,
            bg=Config.CARD_BG, fg="#b0b8c1",
            font=(Config.FONT_FAMILY, 8),
            relief="flat", borderwidth=0,  # 扁平无边框样式
            cursor="hand2", padx=3, pady=0,
            activebackground=Config.CARD_HOVER_BG, activeforeground="#2c3e50",
        )
        self._prev_btn.pack(side=tk.LEFT, fill=tk.Y)  # 左侧垂直填充

        # ---- 中间内容区域 ----
        self._content = tk.Frame(self, bg=Config.CARD_BG)
        # 填充剩余空间，左右各有4像素内边距，上方6px下方2px
        self._content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=(8, 4))

        # 1. 系统名称（居中，粗体）—— 主标题
        sys_display = self.project.system_name or self.project.company_name or "\u65e0\u540d\u79f0"
        if len(sys_display) > 12:
            sys_display = sys_display[:11] + "\u2026"
        self._sys_label = tk.Label(
            self._content, text=sys_display, bg=Config.CARD_BG,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
            anchor="center", fg="#2c3e50",
        )
        self._sys_label.pack(fill=tk.X)

        # 2. 公司名称（居中）—— 仅当两者都有时显示为副标题
        if self.project.system_name and self.project.company_name:
            company_display = self.project.company_name
            if len(company_display) > 14:
                company_display = company_display[:13] + "\u2026"
            self._company_label = tk.Label(
                self._content, text=company_display, bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                anchor="center", fg="#5d6d7e",
            )
            self._company_label.pack(fill=tk.X)
        else:
            self._company_label = None

        # 3. 系统等级（居中，小字）
        if self.project.level:
            self._level_label = tk.Label(
                self._content, text=self.project.level,
                bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
                anchor="center", fg="#8e44ad",
            )
            self._level_label.pack(fill=tk.X)
        else:
            self._level_label = None

        # 属地（居中，小字）
        if self.project.location:
            self._loc_label = tk.Label(
                self._content, text=self.project.location,
                bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
                anchor="center", fg="#7f8c8d",
            )
            self._loc_label.pack(fill=tk.X)
        else:
            self._loc_label = None

        # 4. 证书编号（居中，显示备案状态）
        if self.project.cert_number:
            cert_display = self.project.cert_number
            if len(cert_display) > 18:
                cert_display = cert_display[:17] + "\u2026"
            self._cert_label = tk.Label(
                self._content, text="\U0001f4dc \u5df2\u5907\u6848 " + cert_display,
                bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
                anchor="center", fg="#27ae60",
            )
            self._cert_label.pack(fill=tk.X)
        else:
            self._cert_label = tk.Label(
                self._content, text="\U0001f4dc \u672a\u5907\u6848",
                bg=Config.CARD_BG,
                font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
                anchor="center", fg="#e67e22",
            )
            self._cert_label.pack(fill=tk.X)

        # 5. 交付日期（居中）
        deadline_text = self._format_deadline()
        fg_color = self._get_deadline_color()
        self._deadline_label = tk.Label(
            self._content, text=deadline_text, bg=Config.CARD_BG,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            anchor="center", fg=fg_color,
        )
        self._deadline_label.pack(fill=tk.X, pady=(2, 0))

        # ---- 底部按钮栏第1行：操作按钮（居中） ----
        btn_frame = tk.Frame(self._content, bg=Config.CARD_BG)
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        tk.Frame(btn_frame, bg=Config.CARD_BG).pack(side=tk.LEFT, expand=True)
        self._detail_btn = tk.Button(
            btn_frame, text="\u8be6\u60c5", command=self._on_detail_click,
            bg="#ecf0f1", fg="#2c3e50",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=8, pady=1,
            activebackground="#d5dbdb",
        )
        self._detail_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._edit_btn = tk.Button(
            btn_frame, text="\u7f16\u8f91", command=self._on_edit_click,
            bg="#3498db", fg="white",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=8, pady=1,
            activebackground="#2980b9",
        )
        self._edit_btn.pack(side=tk.LEFT)
        self._copy_btn = tk.Button(
            btn_frame, text="\u590d\u5236", command=self._on_copy_click,
            bg="#27ae60", fg="white",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=8, pady=1,
            activebackground="#1e8449",
        )
        self._copy_btn.pack(side=tk.LEFT, padx=(4, 0))
        tk.Frame(btn_frame, bg=Config.CARD_BG).pack(side=tk.LEFT, expand=True)

        # ---- 底部按钮栏第2行：文件操作（居中） ----
        file_btn_frame = tk.Frame(self._content, bg=Config.CARD_BG)
        file_btn_frame.pack(fill=tk.X, pady=(2, 0))

        tk.Frame(file_btn_frame, bg=Config.CARD_BG).pack(side=tk.LEFT, expand=True)
        self._folder_btn = tk.Button(
            file_btn_frame, text="\U0001f4c2", command=self._on_folder_click,
            bg="#ecf0f1", fg="#2c3e50",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=7, pady=1,
            activebackground="#d5dbdb",
        )
        self._folder_btn.pack(side=tk.LEFT, padx=(0, 2))
        _add_tooltip(self._folder_btn, "打开项目文件夹")
        self._rename_btn = tk.Button(
            file_btn_frame, text="\U0001f4dd", command=self._on_rename_click,
            bg="#f0f2f5", fg="#2c3e50",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=7, pady=1,
            activebackground="#d5dbdb",
        )
        self._rename_btn.pack(side=tk.LEFT, padx=(2, 2))
        _add_tooltip(self._rename_btn, "批量重命名文件")
        self._zip_btn = tk.Button(
            file_btn_frame, text="\U0001f4e6", command=self._on_zip_click,
            bg="#f39c12", fg="white",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=7, pady=1,
            activebackground="#e67e22",
        )
        self._zip_btn.pack(side=tk.LEFT, padx=(2, 2))
        _add_tooltip(self._zip_btn, "打包过程文档")
        self._report_btn = tk.Button(
            file_btn_frame, text="\U0001f4c4", command=self._on_report_print_click,
            bg="#8e44ad", fg="white",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", borderwidth=0, cursor="hand2", padx=7, pady=1,
            activebackground="#7d3c98",
        )
        self._report_btn.pack(side=tk.LEFT, padx=(2, 0))
        _add_tooltip(self._report_btn, "报告打印")
        tk.Frame(file_btn_frame, bg=Config.CARD_BG).pack(side=tk.LEFT, expand=True)

        # ---- 右箭头按钮 ----
        # Unicode \u25b6 为 ▶ 字符，点击可将项目移至下一阶段
        self._next_btn = tk.Button(
            self, text="\u25b6", command=self._on_next_click,
            bg=Config.CARD_BG, fg="#b0b8c1",
            font=(Config.FONT_FAMILY, 8),
            relief="flat", borderwidth=0,
            cursor="hand2", padx=3, pady=0,
            activebackground=Config.CARD_HOVER_BG, activeforeground="#2c3e50",
        )
        self._next_btn.pack(side=tk.RIGHT, fill=tk.Y)  # 右侧垂直填充

    def _format_deadline(self) -> str:
        """格式化截止日期显示文本

        返回包含日历图标、日期和剩余天数提示的格式化字符串。
        无截止日期时返回"无截止日期"，已超期显示"已超期"警告，
        临近截止日期显示"剩N天"提醒。

        Returns:
            str: 格式化后的日期显示文本
        """
        if not self.project.deadline:
            return "\u65e0\u622a\u6b62\u65e5\u671f"  # "无截止日期"
        text = "\U0001f4c5 " + self.project.deadline  # 日历图标 + 日期
        days_left = self._days_until_deadline()  # 计算距截止日期的剩余天数
        if days_left < 0:
            text += " (\u5df2\u8d85\u671f)"  # 已超期
        elif days_left <= Config.DEADLINE_WARNING_DAYS:
            text += f" (\u5269{days_left}\u5929)"  # 剩N天
        return text

    def _on_prev_click(self):
        """左箭头按钮点击处理：调用on_move_prev回调将项目移至上一阶段"""
        if self.on_move_prev:
            self.on_move_prev(self)

    def _on_next_click(self):
        """右箭头按钮点击处理：调用on_move_next回调将项目移至下一阶段"""
        if self.on_move_next:
            self.on_move_next(self)

    def _on_detail_click(self):
        """详情按钮点击处理：调用on_detail回调打开项目详情窗口"""
        if self.on_detail:
            self.on_detail(self)

    def _on_edit_click(self):
        """编辑按钮点击处理：调用on_edit回调打开项目编辑对话框"""
        if self.on_edit:
            self.on_edit(self)

    def _on_copy_click(self):
        """复制按钮点击处理：调用on_copy回调复制当前项目"""
        if self.on_copy:
            self.on_copy(self)

    def _on_folder_click(self):
        """文件夹按钮点击处理：打开项目的本地文件夹"""
        import os, subprocess, sys
        try:
            path = self._find_project_folder()
            if path and os.path.isdir(path):
                if sys.platform == "win32":
                    os.startfile(path)
                else:
                    subprocess.run(["xdg-open", path])
        except Exception:
            pass

    def _find_project_folder(self) -> str:
        """查找项目文件夹路径（优先存储路径，回退关键词搜索）"""
        import os, re
        from utils.config import Config
        # 优先使用存储的路径
        if self.project.folder_path and os.path.isdir(self.project.folder_path):
            return self.project.folder_path
        # 回退：按公司名+系统名+日期搜索
        base = Config.get_data_dir()
        if not os.path.exists(base):
            return ""
        cname = (self.project.company_name or "未命名").replace("/", "_").replace("\\", "_")
        sname = (self.project.system_name or "").replace("/", "_").replace("\\", "_")
        date_str = ""
        if self.project.created_at:
            date_str = self.project.created_at[:10].replace("-", "")[2:]
        # 精确匹配关键词
        for name in os.listdir(base):
            full = os.path.join(base, name)
            if not os.path.isdir(full):
                continue
            if cname in name and (not sname or sname in name) and (not date_str or date_str in name):
                return full
        return ""

    def _on_rename_click(self):
        """一键重命名：修正文件名 + ZIP解压 + 结果报告"""
        import os, re, zipfile, shutil
        from tkinter import messagebox
        try:
            root = self._find_project_folder()
            if not root or not os.path.isdir(root):
                messagebox.showinfo("提示", "未找到项目文件夹")
                return
            cname = (self.project.company_name or "未命名").replace("/", "_").replace("\\", "_")
            sname = (self.project.system_name or "").replace("/", "_").replace("\\", "_")
            new_prefix = f"{cname}-{sname}"

            # match_keyword → (编号, 标准化名称)
            key_map = {
                "保密承诺书": ("02", "保密承诺书"),
                "测评调研表": ("03", "测评调研表"),
                "测评授权书": ("04", "测评授权书"),
                "风险告知书": ("05", "风险告知书"),
                "项目计划书": ("06", "项目计划书"),
                "测评方案": ("07", "测评方案"),
                "归档材料评审记录表": ("08", "测评方案评审表"),
                "测评方案评审表": ("08", "测评方案评审表"),
                "首次会议记录": ("09", "首次会议记录"),
                "测评现场记录表": ("10", "测评现场记录表"),
                "问题汇总": ("11", "问题汇总"),
                "漏洞扫描报告": ("12", "漏洞扫描报告"),
                "项目文档移交清单": ("14", "项目文档移交清单"),
                "末次会议记录": ("15", "末次会议记录"),
                "测评报告-终稿": ("16", "测评报告-终稿"),
                "测评报告评审记录表": ("17", "测评报告评审表"),
                "测评报告评审表": ("17", "测评报告评审表"),
                "服务情况评价表": ("18", "服务情况评价表"),
                "报备表": ("19", "报备表"),
            }

            renamed = 0
            msgs = []  # 操作报告

            # === ZIP解压处理 ===
            for fname in os.listdir(root):
                fpath = os.path.join(root, fname)
                if not os.path.isfile(fpath) or not fname.lower().endswith(".zip"):
                    continue
                # 测评方案评审记录表.zip → 解压并重命名为08
                if "测评方案评审记录表" in fname:
                    try:
                        with zipfile.ZipFile(fpath, "r") as zf:
                            zf.extractall(root)
                        os.remove(fpath)
                        renamed += 1
                        msgs.append(f"解压: {fname} → 提取文件")
                    except Exception as e:
                        msgs.append(f"解压失败: {fname} ({e})")
                # 测评报告评审表.zip → 解压，保留终审，删除初审
                elif "测评报告评审表" in fname:
                    try:
                        with zipfile.ZipFile(fpath, "r") as zf:
                            zf.extractall(root)
                        os.remove(fpath)
                        renamed += 1
                        msgs.append(f"解压: {fname} → 提取文件")
                    except Exception as e:
                        msgs.append(f"解压失败: {fname} ({e})")

            # === 删除包含"初审"的文件 ===
            for fname in os.listdir(root):
                if "初审" in fname:
                    try:
                        os.remove(os.path.join(root, fname))
                        msgs.append(f"删除初审: {fname}")
                    except Exception:
                        pass

            # === 文件重命名 ===
            for fname in os.listdir(root):
                fpath = os.path.join(root, fname)
                if not os.path.isfile(fpath) or fname.endswith(".zip"):
                    continue
                name_no_ext, ext = os.path.splitext(fname)

                m = re.match(r"^(\d{2})-(.+)", name_no_ext)
                if m:
                    num = m.group(1)
                    rest = name_no_ext[len(num) + 1:]
                    for keyword in sorted(key_map, key=len, reverse=True):
                        if keyword in rest:
                            num, target_kw = key_map[keyword]
                            new_name = f"{num}-{new_prefix}-{target_kw}{ext}"
                            if new_name != fname:
                                new_path = os.path.join(root, new_name)
                                if not os.path.exists(new_path):
                                    os.rename(fpath, new_path)
                                    renamed += 1
                                else:
                                    msgs.append(f"跳过(已存在): {new_name}")
                            break
                else:
                    for keyword in sorted(key_map, key=len, reverse=True):
                        if keyword in name_no_ext:
                            num, target_kw = key_map[keyword]
                            new_name = f"{num}-{new_prefix}-{target_kw}{ext}"
                            new_path = os.path.join(root, new_name)
                            if not os.path.exists(new_path):
                                os.rename(fpath, new_path)
                                renamed += 1
                            else:
                                msgs.append(f"跳过(已存在): {new_name}")
                            break

            # === 子目录重命名 ===
            for dname in os.listdir(root):
                dpath = os.path.join(root, dname)
                if not os.path.isdir(dpath):
                    continue
                for keyword, num in {"报告打印": "00", "渗透测试报告": "13"}.items():
                    if keyword in dname and (cname not in dname or sname not in dname):
                        new_dname = f"{num}-{new_prefix}-{keyword}"
                        new_dpath = os.path.join(root, new_dname)
                        if not os.path.exists(new_dpath):
                            os.rename(dpath, new_dpath)
                            renamed += 1
                        break

            # === 结果报告 ===
            if msgs:
                msg_text = "\n".join(msgs[:15])
                if len(msgs) > 15:
                    msg_text += f"\n...共 {len(msgs)} 条"
                messagebox.showinfo("操作报告", msg_text)
            elif renamed:
                messagebox.showinfo("完成", f"已处理 {renamed} 个项目")
            else:
                messagebox.showinfo("提示", "所有文件名已是最新，无需修改")
        except Exception as e:
            messagebox.showerror("错误", f"操作失败: {e}")

    def _on_zip_click(self):
        """打包过程文档：将项目文件夹中的过程文件压缩为ZIP"""
        import os, zipfile
        from tkinter import messagebox
        try:
            root = self._find_project_folder()
            if not root or not os.path.isdir(root):
                messagebox.showinfo("提示", "未找到项目文件夹")
                return
            cname = self.project.company_name or "未命名"
            sname = self.project.system_name or ""
            zip_name = f"{cname}-{sname}-过程文档.zip"
            zip_path = os.path.join(root, zip_name)

            # 需要打包的文件关键词列表
            pack_keywords = [
                "保密承诺书", "测评调研表", "测评授权书", "风险告知书",
                "项目计划书", "测评方案", "首次会议记录", "测评现场记录表",
                "问题汇总", "漏洞扫描报告", "项目文档移交清单", "末次会议记录",
                "服务情况评价表", "报备表",
            ]

            count = 0
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # 打包文件
                for fname in os.listdir(root):
                    fpath = os.path.join(root, fname)
                    if not os.path.isfile(fpath) or fname == zip_name:
                        continue
                    name_no_ext = os.path.splitext(fname)[0]
                    for kw in pack_keywords:
                        if kw in name_no_ext:
                            zf.write(fpath, fname)
                            count += 1
                            break
                # 打包渗透测试报告目录（含目录内所有文件+空目录）
                for dname in os.listdir(root):
                    dpath = os.path.join(root, dname)
                    if os.path.isdir(dpath) and "渗透测试报告" in dname:
                        has_files = False
                        for dirpath, _, filenames in os.walk(dpath):
                            for fn in filenames:
                                fp = os.path.join(dirpath, fn)
                                arcname = os.path.relpath(fp, root).replace("\\", "/")
                                zf.write(fp, arcname)
                                count += 1
                                has_files = True
                        # 空目录也加进去
                        if not has_files:
                            info = zipfile.ZipInfo(dname + "/")
                            zf.writestr(info, "")
                            count += 1

            if count > 0:
                messagebox.showinfo("打包完成",
                    f"已打包 {count} 个文件\n{zip_name}")
            else:
                os.remove(zip_path)
                messagebox.showinfo("提示", "未找到可打包的过程文件")
        except Exception as e:
            messagebox.showerror("错误", f"打包失败: {e}")

    def _on_report_print_click(self):
        """报告打印：弹出编辑框确认后创建XLSX并复制文件"""
        import os, shutil
        from tkinter import messagebox
        from datetime import date
        try:
            proot = self._find_project_folder()
            if not proot or not os.path.isdir(proot):
                messagebox.showinfo("提示", "未找到项目文件夹")
                return

            # 弹出编辑确认框
            data = _show_report_dialog(
                self,
                cname=self.project.company_name or "",
                sname=self.project.system_name or "",
                location=(self.project.location or "").split("-")[0] if self.project.location else "",
                deadline=self.project.deadline or date.today().strftime("%Y-%m-%d"),
            )
            if not data:  # 用户取消
                return

            cname = data["cname"]
            sname = data["sname"]
            prefix = f"{cname}-{sname}"

            # 找到/创建报告打印目录
            report_dir = None
            for dname in os.listdir(proot):
                if "报告打印" in dname and os.path.isdir(os.path.join(proot, dname)):
                    report_dir = os.path.join(proot, dname)
                    break
            if not report_dir:
                report_dir = os.path.join(proot, f"00-{prefix}-报告打印")
                os.makedirs(report_dir, exist_ok=True)

            # 创建 XLSX
            xlsx_name = f"00-{prefix}-测评报告打印信息.xlsx"
            xlsx_path = os.path.join(report_dir, xlsx_name)
            self._create_report_xlsx_data(xlsx_path, data, report_dir, proot)

            # 复制文件到报告打印目录
            copied = 0
            copy_keywords = ["测评授权书", "风险告知书"]
            for fname in os.listdir(proot):
                fpath = os.path.join(proot, fname)
                if not os.path.isfile(fpath):
                    continue
                for kw in copy_keywords:
                    if kw in fname:
                        shutil.copy2(fpath, os.path.join(report_dir, fname))
                        copied += 1
                        break
                if "测评报告-终稿" in fname and fname.lower().endswith(".pdf"):
                    shutil.copy2(fpath, os.path.join(report_dir, fname))
                    copied += 1

            zip_name = f"{cname}-{sname}-过程文档.zip"
            zip_src = os.path.join(proot, zip_name)
            if os.path.exists(zip_src):
                shutil.copy2(zip_src, os.path.join(report_dir, zip_name))
                copied += 1

            messagebox.showinfo("报告打印完成",
                f"已生成 {xlsx_name}\n已复制 {copied} 个文件到报告打印目录")
        except Exception as e:
            messagebox.showerror("错误", f"报告打印失败: {e}")

    def _create_report_xlsx_data(self, path, data, report_dir, root):
        """根据编辑框数据创建测评报告打印信息XLSX"""
        self._create_report_xlsx(path, data["cname"], data["sname"], report_dir, root)
        # 用编辑框数据二次写入
        import openpyxl
        wb = openpyxl.load_workbook(path)
        ws = wb.active
        from openpyxl.styles import Alignment, Border, Side
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin'))
        extra = {
            'B3': data.get("contract", ""),
            'D3': data.get("crm", "是"),
            'J3': data.get("author", ""),
            'K3': data.get("reviewer", ""),
            'L3': data.get("pentester", ""),
            'M3': data.get("conclusion", ""),
            'N3': data.get("seal", ""),
            'S3': data.get("print_req", ""),
            'T3': data.get("leader", ""),
            'U3': data.get("actual_author", ""),
        }
        for ref, val in extra.items():
            cell = ws[ref]
            cell.value = val
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        wb.save(path)

    def _create_report_xlsx(self, path, cname, sname, report_dir, root):
        """创建测评报告打印信息XLSX文件"""
        import os as _os
        import openpyxl
        from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
        from datetime import date

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"

        # 列宽
        widths = {'A': 6, 'B': 30, 'C': 22, 'D': 10, 'E': 10, 'F': 18,
                  'G': 12, 'H': 12, 'I': 12, 'J': 12, 'K': 10, 'L': 10,
                  'M': 16, 'N': 10, 'O': 16, 'P': 16, 'Q': 14, 'R': 14,
                  'S': 16, 'T': 10, 'U': 14}
        for col, w in widths.items():
            ws.column_dimensions[col].width = w

        # 提示行
        ws['G1'] = '（需要签入报告，请确认）'
        ws['G1'].font = Font(color='FF0000', bold=True)

        # 表头 (Row 2)
        headers = ['序号', '合同编号或项目名称', '客户公司全称', '是否录入CRM', '所属地',
                   '系统名称', '编制日期', '审核日期', '批准日期',
                   '编制人（与联盟系统对应）', '审核人', '渗透人员',
                   '测评结论及重大风险隐患数量', '盖章',
                   '等级测评项目基本情况表附件', '授权书及风险告知书附件',
                   '测评报告附件', '测评归档附件', '打印要求',
                   '项目组长联系人', '实际报告编制人']
        header_fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin'))
        for i, h in enumerate(headers, 1):
            cell = ws.cell(row=2, column=i, value=h)
            cell.font = Font(bold=True, size=10)
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.row_dimensions[2].height = 35

        # 数据行 (Row 3，紧接表头无空行)
        date_val = self.project.deadline or date.today().strftime('%Y-%m-%d')
        data = [
            (1, 'A'), (f'{cname}网络安全等级保护测评服务项目', 'B'), (cname, 'C'),
            ('是', 'D'),
            ((self.project.location or '').split('-')[0] if self.project.location else '', 'E'),
            (sname, 'F'),
            (date_val, 'G'), (date_val, 'H'), (date_val, 'I'),
            ('双击打开附件', 'O'), ('双击打开附件', 'P'), ('双击打开附件', 'Q'), ('双击打开附件', 'R'),
        ]
        for val, col in data:
            cell = ws[f'{col}3']
            cell.value = val
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        # 为所有 A-U 列第3行设置完整边框
        for col_idx in range(1, 22):
            cell = ws.cell(row=3, column=col_idx)
            cell.border = thin_border
            if not cell.value:
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        ws.row_dimensions[3].height = 25

        # 合并单元格 G1-U1
        ws.merge_cells('G1:U1')

        # 附件超链接: O=基本情况表, P=授权书+风险告知书, Q=测评报告, R=过程文档
        link_map = {
            'O': ['基本情况表'],
            'P': ['测评授权书', '风险告知书'],
            'Q': ['测评报告-终稿'],
            'R': ['过程文档.zip'],
        }
        for col, keywords in link_map.items():
            found = False
            for kw in keywords:
                for d in [report_dir, root]:
                    if not _os.path.isdir(d):
                        continue
                    for fname in _os.listdir(d):
                        if kw in fname:
                            fpath = _os.path.join(d, fname)
                            cell = ws[f'{col}3']
                            cell.value = fname
                            cell.hyperlink = fpath
                            cell.font = Font(color='0563C1', underline='single', size=10)
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

        wb.save(path)

    def _bind_events(self):
        """绑定鼠标事件到卡片内部所有组件（排除按钮组件，因为它们有独立的command）

        使用递归方式将单击、双击、进入、离开事件绑定到卡片内所有子组件，
        但排除左右箭头和详情/编辑按钮，避免干扰按钮自身的点击事件。
        """
        btn_widgets = {self._prev_btn, self._next_btn,
                       self._detail_btn, self._edit_btn, self._copy_btn,
                       self._folder_btn, self._rename_btn, self._zip_btn,
                       self._report_btn}

        # 先给Frame自身绑定事件
        self.bind("<Button-1>", self._on_click)  # 鼠标左键单击
        self.bind("<Double-Button-1>", self._on_double_click)  # 鼠标左键双击
        self.bind("<Enter>", self._on_enter)  # 鼠标进入组件区域
        self.bind("<Leave>", self._on_leave)  # 鼠标离开组件区域

        def _bind_recursive(widget):
            """递归函数：遍历组件树，为除按钮外的所有组件绑定鼠标事件"""
            if widget not in btn_widgets:
                widget.bind("<Button-1>", self._on_click)  # 绑定单击
                widget.bind("<Double-Button-1>", self._on_double_click)  # 绑定双击
                widget.bind("<Enter>", self._on_enter)  # 绑定鼠标进入
                widget.bind("<Leave>", self._on_leave)  # 绑定鼠标离开
                for child in widget.winfo_children():  # 遍历所有子组件
                    _bind_recursive(child)  # 递归处理子组件

        for child in self.winfo_children():  # 从Frame的直接子组件开始递归绑定
            _bind_recursive(child)

    def _on_click(self, event):
        """鼠标单击事件处理：调用外部设置的回调函数"""
        if self.on_click:
            self.on_click(self)

    def _on_double_click(self, event):
        """鼠标双击事件处理：调用外部设置的回调函数（通常打开编辑对话框）"""
        if self.on_double_click:
            self.on_double_click(self)

    def _on_enter(self, event):
        """鼠标进入卡片区域：未选中状态下切换为悬停背景色"""
        if not self.is_selected:
            self.configure(bg=Config.CARD_HOVER_BG)  # 设置Frame自身背景色
            self._set_bg_recursive(self, Config.CARD_HOVER_BG)  # 递归设置子组件背景色

    def _on_leave(self, event):
        """鼠标离开卡片区域：未选中状态下恢复默认背景色"""
        if not self.is_selected:
            self.configure(bg=Config.CARD_BG)  # 恢复Frame默认背景色
            self._set_bg_recursive(self, Config.CARD_BG)  # 递归恢复子组件背景色

    def _set_bg_recursive(self, widget, color):
        """递归设置组件树的背景色

        遍历组件树，将符合条件（非特殊颜色组件）的背景色统一设置为指定颜色。
        排除按钮、状态条等固定颜色的组件，避免覆盖其设计颜色。

        Args:
            widget: 要处理的根组件
            color: 目标背景色
        """
        try:
            bg = widget.cget("bg")  # 获取组件当前背景色
            # 排除特殊功能组件的固定颜色（状态色、按钮色等）
            if bg not in ("#3498db", "#2ecc71", "#e67e22",
                          "#9b59b6", "#e74c3c", "#1abc9c",
                          "#f39c12", "#95a5a6",
                          "#ecf0f1", "#d5dbdb", "#2980b9",
                          "#b0b8c1", "white"):
                widget.configure(bg=color)  # 设置新背景色
        except tk.TclError:
            pass  # 某些组件可能不支持bg属性，忽略异常

    def set_selected(self, selected: bool):
        """设置卡片的选中状态

        选中时显示蓝色加粗边框，取消选中时恢复默认边框。

        Args:
            selected: True表示选中，False表示取消选中
        """
        self.is_selected = selected  # 更新选中状态标志
        if selected:
            # 选中状态：蓝色2像素边框
            self.configure(highlightbackground="#2196F3",
                           highlightthickness=2)
        else:
            # 取消选中：恢复默认边框颜色和宽度
            self.configure(highlightbackground=Config.CARD_BORDER,
                           highlightthickness=1)
            self.configure(bg=Config.CARD_BG)  # 恢复默认背景色

    def refresh(self):
        """刷新卡片显示

        当项目数据更新后，销毁并重建所有UI子组件以反映最新数据。
        重建后保留原有的回调函数引用，避免功能丢失。
        """
        # 保存当前的回调函数引用
        saved = {
            "on_click": self.on_click,
            "on_double_click": self.on_double_click,
            "on_detail": self.on_detail,
            "on_edit": self.on_edit,
            "on_copy": self.on_copy,
            "on_move_prev": self.on_move_prev,
            "on_move_next": self.on_move_next,
        }
        for widget in self.winfo_children():  # 销毁所有子组件
            widget.destroy()
        self._build_ui()  # 重建UI
        self._bind_events()  # 重新绑定事件
        for k, v in saved.items():  # 恢复保存的回调函数
            setattr(self, k, v)

    def _get_status_color(self) -> str:
        """根据截止日期获取左侧状态颜色条的显示颜色

        Returns:
            str: 颜色代码
                - 灰色 (#95a5a6): 无截止日期
                - 红色 (#e74c3c): 已超期
                - 橙色 (#f39c12): 临近截止日期（警告期内）
                - 绿色 (#2ecc71): 正常（时间充裕）
        """
        if not self.project.deadline:
            return "#95a5a6"  # 无截止日期，灰色
        days_left = self._days_until_deadline()  # 计算剩余天数
        if days_left < 0:
            return "#e74c3c"  # 已超期，红色
        elif days_left <= Config.DEADLINE_WARNING_DAYS:
            return "#f39c12"  # 临近截止日期，橙色警告
        return "#2ecc71"  # 时间充裕，绿色

    def _get_deadline_color(self) -> str:
        """根据截止日期获取日期标签的文字颜色

        Returns:
            str: 颜色代码
                - 灰色 (#95a5a6): 无截止日期
                - 红色 (#e74c3c): 已超期
                - 橙色 (#e67e22): 临近截止日期
                - 绿色 (#27ae60): 正常
        """
        if not self.project.deadline:
            return "#95a5a6"
        days_left = self._days_until_deadline()
        if days_left < 0:
            return "#e74c3c"
        elif days_left <= Config.DEADLINE_WARNING_DAYS:
            return "#e67e22"
        return "#27ae60"

    def _days_until_deadline(self) -> int:
        """计算距离截止日期的剩余天数（负数表示已超期）

        通过日期差值计算，today - deadline 得到正数时为已过天数。
        无截止日期或日期格式无效时返回999（视为远期）。

        Returns:
            int: 剩余天数，负数表示已超期
        """
        if not self.project.deadline:
            return 999  # 无截止日期，返回大数视为远期
        try:
            dl = date.fromisoformat(self.project.deadline)  # 解析日期字符串
            return (dl - date.today()).days  # 计算日期差（正数为未来，负数为过去）
        except (ValueError, TypeError):
            return 999  # 日期格式异常，返回大数
