"""
项目编辑对话框 - 用于新增和编辑项目信息

提供表单输入：
- 公司名称（必填）
- 系统名称（选填）
- 系统备案号（选填）
- 截止日期（可选，含日期选择器）
- 所属阶段（下拉选择）
- 备注信息（多行文本）
"""

import tkinter as tk  # 导入Tkinter GUI库，用于构建桌面应用界面组件
from tkinter import ttk, messagebox  # ttk提供增强组件(Combobox等)，messagebox用于弹窗提示
from datetime import date  # 导入date类，用于日期格式验证
from models.project import Project  # 导入Project模型类，表示一个等保测评项目实体
from models.workflow import WorkflowStage  # 导入WorkflowStage模型类，表示一个流程阶段实体
from ui.calendar_picker import pick_date  # 导入日历选择器函数，弹出日历面板选择日期
from utils.config import Config  # 导入Config配置类，获取字体等UI配置常量
from utils.helpers import get_today_str, bordered_entry  # 导入辅助函数：获取今天字符串、带边框输入框


class ProjectDialog(tk.Toplevel):
    """项目新增/编辑对话框 - 继承自tk.Toplevel（独立顶层窗口）

    模态窗口，用户填写项目信息后确认或取消。
    支持新增和编辑两种模式（编辑模式下预填现有数据）。

    Attributes:
        result: 对话框结果数据字典（确认后设置，取消为None）
            包含字段：company_name, system_name, cert_number, deadline, notes, stage_id
    """

    def __init__(self, parent, title: str = "新增项目",
                 project: Project = None,
                 stages: list[WorkflowStage] = None):
        """初始化对话框

        Args:
            parent: 父级窗口
            title: 对话框标题（新增时默认"新增项目"，编辑时为"编辑项目"）
            project: 编辑模式下的现有项目对象（None表示新增模式）
            stages: 可选的流程阶段列表，用于阶段下拉选择
        """
        super().__init__(parent)  # 调用父类Toplevel初始化
        self.title(title)  # 设置窗口标题
        self.result = None  # 初始化结果数据（None表示用户取消）
        self._project = project  # 保存现有项目引用（编辑模式）
        self._stages = stages or []  # 保存阶段列表（空列表兜底）
        self._is_edit = project is not None  # 判断是否为编辑模式

        self._setup_window()  # 配置窗口属性（大小、最小尺寸等）
        self._build_form()  # 构建表单UI布局
        self._load_data()  # 加载现有数据（编辑模式）或设置默认值
        self._center_window()  # 将窗口居中显示
        self.grab_set()  # 设置为模态窗口（拦截所有事件到本窗口，必须操作完后才能回到父窗口）

    def _setup_window(self):
        """配置窗口属性：大小、最小尺寸、可调整性和背景色"""
        self.geometry("520x520")  # 设置窗口初始大小 520x520 像素
        self.minsize(420, 400)  # 设置窗口最小尺寸（防止用户缩得太小导致UI变形）
        self.resizable(True, True)  # 允许用户调整窗口大小（水平和垂直都可调整）
        self.configure(bg="#ffffff")  # 设置窗口背景色为白色

    def _build_form(self):
        """构建表单UI布局

        表单包含：
        - 底部按钮（取消/保存）
        - 可滚动的表单区域（公司名称、系统名称、备案号、截止日期、阶段选择、备注）
        使用Canvas+Scrollbar实现表单区域的垂直滚动，防止内容过多时溢出。
        """
        # ---- 底部按钮（先pack，确保窗口缩小时不会被挤出） ----
        bottom_frame = tk.Frame(self, bg="#f0f2f5")  # 底部按钮容器，浅灰背景
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)  # 固定在窗口底部，水平填充
        tk.Frame(bottom_frame, bg="#d0d5dd", height=1).pack(fill=tk.X)  # 顶部分隔线

        btn_inner = tk.Frame(bottom_frame, bg="#f0f2f5")  # 按钮内层容器
        btn_inner.pack(fill=tk.X, padx=16, pady=8)  # 水平填充，内边距

        # 取消按钮 - 白色背景，灰色边框，关闭对话框不保存
        tk.Button(btn_inner, text="取消", bg="#ffffff", fg="#2c3e50",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  command=self.destroy, cursor="hand2",
                  padx=16, pady=4, relief="flat",
                  highlightbackground="#d0d5dd", highlightthickness=1,  # 灰色细边框
                  ).pack(side=tk.RIGHT, padx=(6, 0))  # 右侧放置

        # 保存按钮 - 蓝色背景，白色文字，调用确认方法
        tk.Button(btn_inner, text="保存", bg="#3498db", fg="white",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  command=self._on_confirm, cursor="hand2",
                  padx=16, pady=4, relief="flat",
                  ).pack(side=tk.RIGHT)  # 紧挨取消按钮左侧

        # ---- 可滚动表单区域（填充剩余空间） ----
        form_canvas = tk.Canvas(self, bg="#ffffff", highlightthickness=0)  # 表单滚动Canvas容器
        form_scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL,
                                      command=form_canvas.yview)  # 垂直滚动条
        form_canvas.configure(yscrollcommand=form_scrollbar.set)  # Canvas与滚动条联动

        main_frame = tk.Frame(form_canvas, bg="#ffffff", padx=20, pady=15)  # 表单主内容容器
        # 当主内容Frame大小变化时，更新Canvas的滚动区域
        main_frame.bind("<Configure>",
                        lambda e: form_canvas.configure(
                            scrollregion=form_canvas.bbox("all")))

        # 在Canvas中创建窗口对象，放置主内容Frame
        self._form_canvas_window = form_canvas.create_window(
            (0, 0), window=main_frame, anchor="nw", width=480,
        )

        # canvas 宽度变化时同步窗口宽度
        def _on_canvas_resize(event):
            """当Canvas宽度变化时，同步调整内部窗口的宽度"""
            form_canvas.itemconfig(self._form_canvas_window,
                                   width=event.width)
        form_canvas.bind("<Configure>", _on_canvas_resize)  # 绑定Canvas尺寸变化事件

        # 鼠标滚轮支持（绑定到整个对话框以确保始终响应）
        def _on_mousewheel(event):
            """鼠标滚轮事件处理：垂直滚动表单内容"""
            form_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.bind("<MouseWheel>", _on_mousewheel)  # 绑定滚轮事件到对话框窗口

        form_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)  # 滚动条：右侧，垂直填充
        form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Canvas：左侧，填充剩余空间

        self._main_frame = main_frame  # 保存主内容Frame的引用

        # 标题 - 显示窗口标题（新增/编辑项目）
        tk.Label(main_frame, text=self.title(),
                 bg="#ffffff", fg="#2c3e50",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_HEADER, "bold"),
                 ).pack(anchor="w", pady=(0, 15))  # 左对齐，下方15px间距

        # 公司名称输入 - 必填字段（带星号标记）
        tk.Label(main_frame, text="公司名称 *", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")  # 标签左对齐
        self._company_var = tk.StringVar()  # 创建StringVar变量，用于双向绑定输入框值
        self._company_entry, c_outer = bordered_entry(
            main_frame, textvariable=self._company_var,  # bordered_entry返回(输入框, 外边框Frame)
        )
        c_outer.pack(fill=tk.X, pady=(2, 5))  # 水平填充，上下间距

        # 系统名称输入 - 选填字段
        tk.Label(main_frame, text="系统名称", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        self._system_var = tk.StringVar()  # 系统名称的StringVar变量
        self._system_entry, s_outer = bordered_entry(
            main_frame, textvariable=self._system_var,
        )
        s_outer.pack(fill=tk.X, pady=(2, 5))

        # 证书编号 - 选填字段（格式：11位数字-5位数字）
        tk.Label(main_frame, text="证书编号", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        self._filing_var = tk.StringVar()  # 备案号的StringVar变量
        self._filing_entry, f_outer = bordered_entry(
            main_frame, textvariable=self._filing_var,
        )
        f_outer.pack(fill=tk.X, pady=(2, 10))

        # 截止日期输入 - 带日历选择器
        tk.Label(main_frame, text="截止日期", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        date_frame = tk.Frame(main_frame, bg="#ffffff")  # 日期输入行容器
        date_frame.pack(fill=tk.X, pady=(2, 5))

        self._deadline_var = tk.StringVar()  # 截止日期的StringVar变量
        self._deadline_entry, dl_outer = bordered_entry(
            date_frame, textvariable=self._deadline_var,
            width=24,  # 输入框宽度24字符
        )
        dl_outer.pack(side=tk.LEFT)  # 左侧放置输入框

        # 日历选择按钮 - 点击弹出日历面板可视化选择日期
        tk.Button(
            date_frame, text="\U0001f4c5", command=self._open_calendar,  # 日历图标
            bg="#ffffff", fg="#3498db", relief="flat",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_LARGE),
            cursor="hand2", padx=4, pady=0,
            activebackground="#ecf0f1",
        ).pack(side=tk.LEFT, padx=(4, 0))  # 紧挨输入框，左间距4px

        # 日期格式提示
        tk.Label(date_frame, text=" (YYYY-MM-DD)", bg="#ffffff",
                 fg="#95a5a6",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 ).pack(side=tk.LEFT)

        # 快捷日期按钮行 - 提供"今天"、"一周后"、"一月后"、"清除"快捷操作
        quick_frame = tk.Frame(main_frame, bg="#ffffff")
        quick_frame.pack(fill=tk.X, pady=(0, 10))  # 下方10px间距

        # "今天"按钮 - 填入当天日期
        tk.Button(quick_frame, text="今天", bg="#ecf0f1", relief="flat",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  command=lambda: self._deadline_var.set(get_today_str()),
                  cursor="hand2").pack(side=tk.LEFT, padx=(0, 5))
        # "一周后"按钮 - 填入7天后的日期
        tk.Button(quick_frame, text="一周后", bg="#ecf0f1", relief="flat",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  command=self._set_one_week_later,
                  cursor="hand2").pack(side=tk.LEFT, padx=(0, 5))
        # "一月后"按钮 - 填入30天后的日期
        tk.Button(quick_frame, text="一月后", bg="#ecf0f1", relief="flat",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  command=self._set_one_month_later,
                  cursor="hand2").pack(side=tk.LEFT, padx=(0, 5))
        # "清除"按钮 - 清空日期输入
        tk.Button(quick_frame, text="清除", bg="#ecf0f1", relief="flat",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  command=lambda: self._deadline_var.set(""),
                  cursor="hand2").pack(side=tk.LEFT)

        # 所属阶段下拉选择
        tk.Label(main_frame, text="所属阶段", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        self._stage_var = tk.StringVar()  # 阶段选择的StringVar变量
        stage_names = [s.name for s in self._stages]  # 提取所有阶段名称列表
        self._stage_combo = ttk.Combobox(
            main_frame, textvariable=self._stage_var,
            values=stage_names, state="readonly",  # 只读下拉框，防止用户输入
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
        )
        self._stage_combo.pack(fill=tk.X, pady=(2, 10))  # 水平填充

        # 备注输入（带滚动条和外边框的多行文本框）
        tk.Label(main_frame, text="备注信息", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")

        notes_outer = tk.Frame(main_frame, bg="#d0d5dd")  # 外边框Frame（1像素灰线效果）
        notes_outer.pack(fill=tk.BOTH, expand=True, pady=(2, 5))  # 双向填充，可扩展

        notes_inner = tk.Frame(notes_outer, bg="#ffffff")  # 内层白色Frame（通过1px边距露出外层灰色实现边框）
        notes_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)  # 1像素边距露出灰色边框

        self._notes_text = tk.Text(
            notes_inner,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
            height=5, wrap="word",  # 5行高度，按单词换行
            relief="flat", borderwidth=0,  # 扁平无边框（边框由外层Frame实现）
        )
        # 创建垂直滚动条并绑定到文本框
        self._notes_scrollbar = tk.Scrollbar(
            notes_inner, orient=tk.VERTICAL, command=self._notes_text.yview,
        )
        self._notes_text.configure(yscrollcommand=self._notes_scrollbar.set)  # 文本框与滚动条联动

        self._notes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)  # 滚动条：右侧，垂直填充
        self._notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # 文本框：左侧，填充剩余空间

        # 键盘快捷键绑定
        self.bind("<Return>", lambda e: self._on_confirm())  # 回车键：确认保存
        self.bind("<Escape>", lambda e: self.destroy())  # Esc键：取消关闭

    def _load_data(self):
        """编辑模式下加载现有项目数据到表单，新增模式设置默认值"""
        if self._project:
            # 编辑模式：将现有项目的值填入对应表单字段
            self._company_var.set(self._project.company_name)
            self._system_var.set(self._project.system_name)
            self._filing_var.set(self._project.cert_number)
            self._deadline_var.set(self._project.deadline)

            # 根据项目的stage_id匹配并选中对应的阶段下拉项
            for stage in self._stages:
                if stage.id == self._project.stage_id:
                    self._stage_var.set(stage.name)  # 填入阶段名称
                    break
            if not self._stage_var.get() and self._stages:
                self._stage_combo.current(0)  # 未匹配到时默认选第一个

            # 加载备注内容到文本框
            if self._project.notes:
                self._notes_text.insert("1.0", self._project.notes)  # 从第1行第0列开始插入
        else:
            # 新增模式：默认选择第一个流程阶段
            if self._stages:
                self._stage_combo.current(0)  # 选中Combobox的第一项

        self._company_entry.focus_set()  # 将输入焦点设置到公司名称输入框（方便用户立刻输入）

    def _open_calendar(self):
        """打开日历选择器，将选中日期填入输入框"""
        result = pick_date(self, self._deadline_var.get())  # 弹出日历面板，传入当前日期作为初始值
        if result is not None:  # 用户选择了日期（非取消）
            self._deadline_var.set(result)  # 将选中的日期字符串填入输入框

    def _set_one_week_later(self):
        """设置截止日期为一周后（当前日期+7天）"""
        from datetime import timedelta  # 导入timedelta用于日期计算
        d = date.today() + timedelta(days=7)  # 计算7天后的日期
        self._deadline_var.set(d.strftime("%Y-%m-%d"))  # 格式化为YYYY-MM-DD并设置

    def _set_one_month_later(self):
        """设置截止日期为一个月后（当前日期+30天）"""
        from datetime import timedelta  # 导入timedelta用于日期计算
        d = date.today() + timedelta(days=30)  # 计算30天后的日期
        self._deadline_var.set(d.strftime("%Y-%m-%d"))  # 格式化为YYYY-MM-DD并设置

    def _on_confirm(self):
        """确认按钮处理：验证输入并收集表单数据

        验证规则：
        - 公司名称和系统名称至少填写一个
        - 截止日期如果填写，必须为YYYY-MM-DD格式
        - 通过验证后将所有表单数据存入self.result并关闭窗口
        """
        company_name = self._company_var.get().strip()  # 获取并去除公司名称首尾空格
        system_name = self._system_var.get().strip()  # 获取并去除系统名称首尾空格

        # 验证：至少需要填写公司名称或系统名称之一
        if not company_name and not system_name:
            messagebox.showwarning("输入提示", "公司名称和系统名称至少填写一个",
                                   parent=self)
            self._company_entry.focus_set()  # 焦点回到公司名称输入框
            return

        # 日期格式验证
        deadline = self._deadline_var.get().strip()
        if deadline:
            try:
                date.fromisoformat(deadline)  # 尝试解析日期格式，无效则抛出异常
            except (ValueError, TypeError):
                messagebox.showwarning("输入提示",
                                       "日期格式不正确，请使用 YYYY-MM-DD 格式",
                                       parent=self)
                return

        # 获取阶段ID（通过名称匹配阶段列表中的对应ID）
        stage_name = self._stage_var.get()
        stage_id = ""
        for s in self._stages:
            if s.name == stage_name:
                stage_id = s.id  # 找到匹配的阶段ID
                break

        # 收集所有表单结果到字典
        self.result = {
            "company_name": company_name,
            "system_name": system_name,
            "cert_number": self._filing_var.get().strip(),  # 备案号
            "deadline": deadline,  # 截止日期
            "notes": self._notes_text.get("1.0", "end-1c").strip(),  # 备注内容（从第1行0列到末尾-1字符，去掉末尾换行符）
            "stage_id": stage_id,  # 阶段ID
        }
        self.destroy()  # 关闭对话框

    def _center_window(self):
        """窗口居中显示 - 相对于父窗口计算居中位置"""
        self.update_idletasks()  # 等待所有待处理任务完成，获取准确的窗口尺寸
        w = self.winfo_width()  # 本窗口宽度
        h = self.winfo_height()  # 本窗口高度
        pw = self.master.winfo_width()  # 父窗口宽度
        ph = self.master.winfo_height()  # 父窗口高度
        px = self.master.winfo_rootx()  # 父窗口左上角X坐标
        py = self.master.winfo_rooty()  # 父窗口左上角Y坐标
        x = px + (pw - w) // 2  # 居中X坐标：父窗口中心 - 本窗口一半宽度
        y = py + (ph - h) // 2  # 居中Y坐标：父窗口中心 - 本窗口一半高度
        self.geometry(f"+{x}+{y}")  # 设置窗口位置


def show_project_dialog(parent, title: str = "新增项目",
                        project: Project = None,
                        stages: list[WorkflowStage] = None) -> dict | None:
    """显示项目编辑对话框的便捷函数

    创建对话框实例并等待用户操作完成，返回结果数据。
    这是外部调用项目对话框的推荐方式。

    Args:
        parent: 父级窗口
        title: 对话框标题（"新增项目"或"编辑项目"）
        project: 编辑模式下的现有项目（None为新增模式）
        stages: 流程阶段列表

    Returns:
        dict | None: 用户确认后返回包含表单数据的字典，取消返回None
    """
    dialog = ProjectDialog(parent, title, project, stages)  # 创建对话框实例
    parent.wait_window(dialog)  # 阻塞等待对话框关闭（模态行为）
    return dialog.result  # 返回对话框结果数据
