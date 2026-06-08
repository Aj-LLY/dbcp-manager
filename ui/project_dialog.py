"""
项目编辑对话框模块 -- 等保测评进度管理系统

本模块提供项目的新增与编辑功能，以模态对话框形式与用户交互。
主要功能包括：
  - 项目基本信息录入（公司名称、可编辑多系统表格、证书编号、属地等）
  - 日期选择（下证日期和交付日期，均支持日历控件和快捷按钮）
  - 上传备案证OCR自动识别填充字段
  - 项目文件夹路径选择与目录结构创建
  - 流程阶段下拉选择
  - 表单验证（必填校验、日期格式、证书编号格式）

外部使用者应通过 show_project_dialog() 便捷函数调用，
该函数创建对话框实例、阻塞等待用户操作，最终返回包含表单数据的字典或 None。

使用示例：
    result = show_project_dialog(parent, title="新增项目", stages=stages)
    if result:
        # result 为包含所有表单字段的 dict
        # 包含 "systems" 列表（每个系统一行）和顶层向后兼容字段
        ...
"""

# =============================================================================
# 标准库导入
# =============================================================================
import os                       # 操作系统接口：创建目录、路径分隔符替换

from datetime import date, timedelta       # 日期处理：date 用于日期格式验证，timedelta 用于日期偏移计算

# =============================================================================
# 第三方库导入
# =============================================================================
import tkinter as tk            # Tkinter GUI 库：构建桌面应用窗口和组件
from tkinter import ttk, messagebox, filedialog  # ttk 增强组件 | messagebox 弹窗 | filedialog 文件/文件夹选择

# =============================================================================
# 项目内部模块导入
# =============================================================================
from models.project import Project         # Project 数据模型：表示一个等保测评项目实体
from models.workflow import WorkflowStage   # WorkflowStage 数据模型：表示流程阶段
from ui.calendar_picker import pick_date    # 日历选择器便捷函数：弹出日历面板供用户选择日期
from utils.config import Config            # 全局配置：字体族、字号、颜色等 UI 常量
from utils.helpers import (                # 辅助工具函数
    get_today_str,                         # 获取今天日期的 YYYY-MM-DD 字符串
    bordered_entry,                        # 创建带灰色外边框的输入框组件
    validate_cert_number,                  # 验证证书编号格式（11位数字 - 5位数字）
)
from utils.province_data import (          # 全国省市区静态数据
    PROVINCE_CITIES,                       # 省级 → 市级列表字典（供 _on_province_change 使用）
    PROVINCES,                             # 省级名称列表（供省级下拉框 values 使用）
)
from ui.dialog_project_ocr import (        # OCR 备案证识别模块（从项目对话框抽取）
    on_upload_cert,                        # 上传备案证 → 后台 OCR 线程
    fill_cert_result,                      # OCR 结果填充到表单字段
    archive_cert_file,                     # 归档备案证文件到项目目录
    ocr_failed,                            # OCR 失败时的恢复与提示
)


# =============================================================================
# 模块级常量
# =============================================================================

# 系统等级下拉选项（每行共用）
LEVEL_VALUES = ["", "第一级", "第二级", "第三级", "第四级", "第五级"]

# =============================================================================
# ProjectDialog -- 项目新增/编辑模态对话框
# =============================================================================

class ProjectDialog(tk.Toplevel):
    """项目新增/编辑对话框。

    以模态顶层窗口（Toplevel）形式呈现，提供完整的项目信息录入界面。
    支持两种模式：
      - 新增模式（project=None）：表单为空，默认选中第一个流程阶段。
      - 编辑模式（project 非空）：表单预填现有项目数据，用户修改后保存。

    窗口布局：
      - 顶部：滚动区域（Canvas + Scrollbar），包含所有表单字段
      - 底部固定栏：取消按钮（右）+ 保存按钮（左），灰色分隔线

    表单字段：
      1. 公司名称 *（必填之一）
      2. 可编辑多系统表格（每行含系统名称、等级、证书编号、下证日期、省/市属地）
         + "+ 添加系统" 按钮
      3. 上传备案证识别按钮（OCR 自动填充）
      4. 交付日期（日历选择器 + 今天/一周后/一月后/清除快捷按钮）
      5. 所属阶段（只读下拉选择）
      6. 项目文件夹（路径选择 + 创建目录按钮）
      7. 备注信息（多行文本，带滚动条和灰色外边框）

    键盘快捷键：
      - Enter：确认保存
      - Esc：取消关闭

    Attributes:
        result: dict | None
            用户确认保存后为包含所有表单字段的字典，取消时为 None。
            字典包含："systems" 列表（每行一个 dict）以及顶层向后兼容字段
            (company_name, system_name, cert_number, issue_date, level,
             location, deadline, notes, stage_id, folder_path)
    """

    def __init__(self, parent, title: str = "新增项目",
                 project: Project = None,
                 stages: list[WorkflowStage] = None,
                 all_projects: list = None):
        """初始化项目新增/编辑对话框。

        Args:
            parent: 父级窗口。
            title: 对话框标题。
            project: 待编辑的现有项目对象（None=新增）。
            stages: 流程阶段列表。
            all_projects: 合并卡片中的所有项目（用于多系统表格展示）。
        """
        super().__init__(parent)
        self.title(title)
        self.result = None
        self._project = project
        self._all_projects = all_projects  # 多系统表格数据
        self._stages = stages or []
        self._is_edit = project is not None
        self._sys_rows_list = []   # list[dict]: 每个元素为一行系统数据的控件引用

        # ---- 按顺序执行窗口初始化步骤 ----
        self._setup_window()     # ① 配置窗口基本属性（大小、最小尺寸、背景色）
        self._build_form()       # ② 构建表单 UI 布局（所有控件和容器）
        self._load_data()        # ③ 编辑模式下预填数据，或设置新增模式的默认值
        self._center_window()    # ④ 将窗口相对于父窗口居中显示
        self.grab_set()          # ⑤ 设置模态（拦截所有事件，必须关闭本窗口后才能操作父窗口）

    # =========================================================================
    # 向后兼容属性 —— 指向第一行系统数据的 StringVar / Combobox
    # 这些 @property 确保旧代码（如 OCR 模块、_load_data、_on_confirm、
    # _get_location、_on_create_folders）中对 self._system_var 等属性的
    # .get() / .set() 调用依然有效。
    # =========================================================================

    @property
    def _system_var(self):
        """向后兼容：返回第一行系统数据的 system_name StringVar。"""
        if self._sys_rows_list:
            return self._sys_rows_list[0]["system_var"]
        return tk.StringVar()

    @property
    def _level_var(self):
        """向后兼容：返回第一行系统数据的 level StringVar。"""
        if self._sys_rows_list:
            return self._sys_rows_list[0]["level_var"]
        return tk.StringVar()

    @property
    def _cert_var(self):
        """向后兼容：返回第一行系统数据的 cert_number StringVar。"""
        if self._sys_rows_list:
            return self._sys_rows_list[0]["cert_var"]
        return tk.StringVar()

    @property
    def _issue_date_var(self):
        """向后兼容：返回第一行系统数据的 issue_date StringVar。"""
        if self._sys_rows_list:
            return self._sys_rows_list[0]["issue_date_var"]
        return tk.StringVar()

    @property
    def _province_var(self):
        """向后兼容：返回第一行系统数据的 province StringVar。"""
        if self._sys_rows_list:
            return self._sys_rows_list[0]["province_var"]
        return tk.StringVar()

    @property
    def _city_var(self):
        """向后兼容：返回第一行系统数据的 city StringVar。"""
        if self._sys_rows_list:
            return self._sys_rows_list[0]["city_var"]
        return tk.StringVar()

    @property
    def _province_combo(self):
        """向后兼容：返回第一行系统数据的 province ttk.Combobox。"""
        if self._sys_rows_list:
            return self._sys_rows_list[0]["province_combo"]
        return None

    @property
    def _city_combo(self):
        """向后兼容：返回第一行系统数据的 city ttk.Combobox。"""
        if self._sys_rows_list:
            return self._sys_rows_list[0]["city_combo"]
        return None

    # =========================================================================
    # 窗口配置
    # =========================================================================

    def _setup_window(self):
        """配置对话框窗口的基本属性。

        设置项：
          - 初始尺寸：540×620 像素（加高以容纳属地、OCR、文件夹等新增字段）
          - 最小尺寸：420×480 像素（防止用户缩得太小导致 UI 变形）
          - 可调整大小：水平和垂直均可拖拽调整
          - 背景色：白色 #ffffff
        """
        self.geometry("680x700")         # 加宽以容纳多系统表格
        self.minsize(500, 480)           # 设置窗口最小宽度420px，最小高度480px
        self.resizable(True, True)       # 允许用户水平和垂直方向调整窗口大小
        self.configure(bg="#ffffff")     # 窗口背景色设为白色

    # =========================================================================
    # 表单 UI 构建
    # =========================================================================

    def _build_form(self):
        """构建项目的完整表单UI布局。

        布局结构（从上到下）：
          1. 底部固定按钮栏（先 pack，保证窗口缩小时不会被挤出视口）
          2. 可滚动的表单内容区域（Canvas + Scrollbar + 内嵌 Frame）
             - 标题行
             - 公司名称输入框（必填标记 *）
             - 可编辑多系统表格（每行含名称/等级/证书/下证日期/省-市属地）
               + "+ 添加系统" 按钮
             - 上传备案证识别按钮 + OCR 状态标签
             - 交付日期（日历按钮 + 快捷日期按钮）
             - 所属阶段下拉框
             - 项目文件夹路径（浏览 + 创建目录）
             - 备注信息多行文本框（带滚动条和灰色外边框）

        组件层次：
            self (Toplevel)
              ├── bottom_frame [Frame, fill=X, side=BOTTOM]
              │     ├── 分隔线 [Frame, height=1]
              │     └── btn_inner [Frame]
              │           ├── "取消" [Button, side=RIGHT] → self.destroy
              │           └── "保存" [Button, side=RIGHT] → self._on_confirm
              └── form_canvas [Canvas, fill=BOTH, side=LEFT]
                    └── main_frame [Frame, via create_window]
                          ├── 标题 [Label]
                          ├── 各种表单字段控件（含多系统表格）
                          └── 备注文本框 + 滚动条
        """
        # =====================================================================
        # 底部按钮栏（先 pack，确保窗口缩小时按钮不会被挤出视口）
        # =====================================================================
        # 底部容器 Frame，浅灰色背景，固定在窗口底部，水平填充
        bottom_frame = tk.Frame(self, bg="#f0f2f5")
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        # 底部分隔线（1px 灰色横线，视觉上与内容区域分隔）
        tk.Frame(bottom_frame, bg="#d0d5dd", height=1).pack(fill=tk.X)

        # 按钮内层容器，用于控制按钮边距
        btn_inner = tk.Frame(bottom_frame, bg="#f0f2f5")
        btn_inner.pack(fill=tk.X, padx=16, pady=8)

        # "取消"按钮 -- 白色背景、灰色边框、深色文字，点击调用 self.destroy 关闭对话框
        tk.Button(btn_inner, text="取消", bg="#ffffff", fg="#2c3e50",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  command=self.destroy, cursor="hand2",
                  padx=16, pady=4, relief="flat",
                  highlightbackground="#d0d5dd", highlightthickness=1,    # 1px 灰色细边框
                  ).pack(side=tk.RIGHT, padx=(6, 0))

        # "保存"按钮 -- 蓝色背景、白色文字，点击调用 _on_confirm 验证并保存
        tk.Button(btn_inner, text="保存", bg="#3498db", fg="white",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  command=self._on_confirm, cursor="hand2",
                  padx=16, pady=4, relief="flat",
                  ).pack(side=tk.RIGHT)

        # =====================================================================
        # 可滚动的表单内容区域（Canvas + Scrollbar）
        # =====================================================================
        # Canvas 用作可滚动容器，白色背景，无高亮边框
        form_canvas = tk.Canvas(self, bg="#ffffff", highlightthickness=0)
        # 垂直滚动条，绑定到 Canvas 的 yview 方法
        form_scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL,
                                      command=form_canvas.yview)
        # 将滚动条与 Canvas 双向绑定：拖动滚动条 → Canvas 滚动
        form_canvas.configure(yscrollcommand=form_scrollbar.set)

        # 表单主内容 Frame（所有表单控件将放在这里面）
        main_frame = tk.Frame(form_canvas, bg="#ffffff", padx=20, pady=15)

        # 当 main_frame 大小变化时，更新 Canvas 的滚动区域（scrollregion）
        main_frame.bind("<Configure>",
                        lambda e: form_canvas.configure(
                            scrollregion=form_canvas.bbox("all")))

        # 在 Canvas 中创建窗口对象（window），将 main_frame 嵌入 Canvas
        self._form_canvas_window = form_canvas.create_window(
            (0, 0), window=main_frame, anchor="nw", width=480,
        )

        # Canvas 宽度变化时，同步调整内部主 Frame 的宽度
        def _on_canvas_resize(event):
            """Canvas 尺寸变化事件处理：调整内部窗口宽度与 Canvas 一致。"""
            form_canvas.itemconfig(self._form_canvas_window,
                                   width=event.width)
        form_canvas.bind("<Configure>", _on_canvas_resize)

        # 鼠标滚轮支持：绑定到对话框自身以确保始终响应滚轮事件
        def _on_mousewheel(event):
            """鼠标滚轮事件处理：垂直滚动 Canvas 内容。

            每次滚轮刻度滚动约 1/120 行，负号用于反转方向
            （Windows 上向上滚动 delta 为正）。
            """
            form_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.bind("<MouseWheel>", _on_mousewheel)

        # 布局：滚动条在右侧，Canvas 填充左侧剩余空间
        form_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 保存 main_frame 引用，供后续方法使用
        self._main_frame = main_frame

        # =====================================================================
        # 表单内容：标题行
        # =====================================================================
        tk.Label(main_frame, text=self.title(),
                 bg="#ffffff", fg="#2c3e50",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_HEADER, "bold"),
                 ).pack(anchor="w", pady=(0, 10))

        # =====================================================================
        # 1. 公司名称（必填字段，所有系统共用）
        # =====================================================================
        tk.Label(main_frame, text="公司名称 *", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        self._company_var = tk.StringVar()            # 公司名称的 StringVar 变量
        self._company_entry, c_outer = bordered_entry(  # 创建带灰色外边框的输入框
            main_frame, textvariable=self._company_var,
        )
        c_outer.pack(fill=tk.X, pady=(2, 5))

        # =====================================================================
        # 2. 可编辑多系统表格
        # =====================================================================
        tk.Label(main_frame, text="系统列表", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL, "bold"),
                 ).pack(anchor="w")
        self._sys_container = tk.Frame(main_frame, bg="#ffffff")
        self._sys_container.pack(fill=tk.X, pady=(2, 5))

        # 默认添加第一个空行
        self._add_sys_row()

        # "+ 添加系统" 按钮
        tk.Button(
            main_frame, text="+ 添加系统", command=self._add_sys_row,
            bg="#ecf0f1", fg="#2c3e50", relief="flat", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            padx=10, pady=2, activebackground="#d5dbdb",
        ).pack(anchor="w", pady=(0, 5))

        # =====================================================================
        # OCR 状态提示标签（全局）
        self._ocr_status = tk.Label(main_frame, text="", bg="#ffffff",
                                     font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
                                     fg="#7f8c8d")
        self._ocr_status.pack(anchor="w", pady=(0, 5))

        # =====================================================================
        # 4. 交付日期（日历选择器 + 快捷日期按钮）
        # =====================================================================
        tk.Label(main_frame, text="交付日期", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        date_frame = tk.Frame(main_frame, bg="#ffffff")
        date_frame.pack(fill=tk.X, pady=(2, 5))
        self._deadline_var = tk.StringVar()               # 交付日期的 StringVar 变量
        self._deadline_entry, dl_outer = bordered_entry(
            date_frame, textvariable=self._deadline_var, width=24,
        )
        dl_outer.pack(side=tk.LEFT)
        # 日历按钮 -- 弹出日历选择器
        tk.Button(
            date_frame, text="\U0001f4c5", command=self._open_calendar,
            bg="#ffffff", fg="#3498db", relief="flat",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_LARGE),
            cursor="hand2", padx=4, pady=0,
            activebackground="#ecf0f1",
        ).pack(side=tk.LEFT, padx=(4, 0))
        # 日期格式提示标签
        tk.Label(date_frame, text=" (YYYY-MM-DD)", bg="#ffffff",
                 fg="#95a5a6",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 ).pack(side=tk.LEFT)

        # 快捷日期按钮行
        quick_frame = tk.Frame(main_frame, bg="#ffffff")
        quick_frame.pack(fill=tk.X, pady=(0, 10))
        # "今天" -- 填入今天日期
        tk.Button(quick_frame, text="今天", bg="#ecf0f1", relief="flat",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  command=lambda: self._deadline_var.set(get_today_str()),
                  cursor="hand2").pack(side=tk.LEFT, padx=(0, 5))
        # "一周后" -- 填入 7 天后的日期
        tk.Button(quick_frame, text="一周后", bg="#ecf0f1", relief="flat",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  command=self._set_one_week_later,
                  cursor="hand2").pack(side=tk.LEFT, padx=(0, 5))
        # "一月后" -- 填入 30 天后的日期
        tk.Button(quick_frame, text="一月后", bg="#ecf0f1", relief="flat",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  command=self._set_one_month_later,
                  cursor="hand2").pack(side=tk.LEFT, padx=(0, 5))
        # "清除" -- 清空日期输入框
        tk.Button(quick_frame, text="清除", bg="#ecf0f1", relief="flat",
                  font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                  command=lambda: self._deadline_var.set(""),
                  cursor="hand2").pack(side=tk.LEFT)

        # =====================================================================
        # 5. 所属阶段（只读下拉选择）
        # =====================================================================
        tk.Label(main_frame, text="所属阶段", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        self._stage_var = tk.StringVar()                # 阶段选择的 StringVar 变量
        stage_names = [s.name for s in self._stages]    # 提取所有阶段名称列表
        self._stage_combo = ttk.Combobox(
            main_frame, textvariable=self._stage_var,
            values=stage_names, state="readonly",       # 只读下拉框
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
        )
        self._stage_combo.pack(fill=tk.X, pady=(2, 5))

        # =====================================================================
        # 6. 项目文件夹管理（路径输入 + 浏览 + 创建目录）
        # =====================================================================
        tk.Label(main_frame, text="项目文件夹", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        folder_row = tk.Frame(main_frame, bg="#ffffff")
        folder_row.pack(fill=tk.X, pady=(2, 10))
        self._folder_path_var = tk.StringVar()            # 文件夹路径的 StringVar 变量
        self._folder_entry, fp_outer = bordered_entry(
            folder_row, textvariable=self._folder_path_var,
        )
        fp_outer.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # "选择" 按钮 -- 打开系统文件夹选择对话框
        tk.Button(
            folder_row, text="选择", command=self._on_browse_folder,
            bg="#ecf0f1", fg="#2c3e50", relief="flat", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            padx=8, pady=2, activebackground="#d5dbdb",
        ).pack(side=tk.LEFT, padx=(4, 0))
        # "创建目录" 按钮 -- 在指定路径下创建项目子目录
        tk.Button(
            folder_row, text="创建目录", command=self._on_create_folders,
            bg="#f0f2f5", fg="#2c3e50", relief="flat", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            padx=8, pady=2, activebackground="#d5dbdb",
        ).pack(side=tk.LEFT, padx=(4, 0))

        # =====================================================================
        # 7. 备注信息（多行文本输入，带滚动条和灰色外边框）
        # =====================================================================
        tk.Label(main_frame, text="备注信息", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")

        # 灰色外边框 Frame（通过 1px 内边距露出灰色背景模拟边框效果）
        notes_outer = tk.Frame(main_frame, bg="#d0d5dd")
        notes_outer.pack(fill=tk.BOTH, expand=True, pady=(2, 5))

        # 内层白色 Frame，1px 边距露出外层的灰色，形成视觉边框
        notes_inner = tk.Frame(notes_outer, bg="#ffffff")
        notes_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # 多行文本输入框
        self._notes_text = tk.Text(
            notes_inner,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
            height=5, wrap="word",         # 5 行可见高度，按单词边界自动换行
            relief="flat", borderwidth=0,  # 扁平无边框（边框由外层 Frame 实现）
        )
        # 垂直滚动条，绑定到文本框
        self._notes_scrollbar = tk.Scrollbar(
            notes_inner, orient=tk.VERTICAL, command=self._notes_text.yview,
        )
        self._notes_text.configure(yscrollcommand=self._notes_scrollbar.set)  # 双向绑定

        # 布局：滚动条右侧，文本框填充左侧剩余空间
        self._notes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # =====================================================================
        # 键盘快捷键绑定
        # =====================================================================
        self.bind("<Return>", lambda e: self._on_confirm())   # Enter 键 → 确认保存
        self.bind("<Escape>", lambda e: self.destroy())        # Esc 键 → 关闭对话框

    # =========================================================================
    # 多系统行管理
    # =========================================================================

    def _add_sys_row(self, data: dict = None):
        """添加一行可编辑的系统数据到系统表格容器中。

        每行包含：
          - 系统名称输入框（Entry）
          - 系统等级下拉框（Combobox，只读）
          - 证书编号输入框（Entry）
          - 下证日期输入框（Entry）+ 日历按钮
          - 属地下拉框（省-市两级联动 Combobox）
          - "复制"按钮
          - "删除"按钮（至少保留一行时显示）

        Args:
            data: 可选的预填数据字典，键包括：
                system_name, level, cert_number, issue_date, province, city

        Returns:
            dict: 行数据引用字典，包含所有 StringVar 和控件引用。
        """
        data = data or {}
        idx = len(self._sys_rows_list) + 1

        # ---- 行容器（浅灰背景，形成视觉分组）----
        row_frame = tk.Frame(self._sys_container, bg="#f0f2f5", padx=5, pady=3)
        row_frame.pack(fill=tk.X, pady=(0, 3))

        # ---- 行标题：系统 #N ----
        hdr = tk.Frame(row_frame, bg="#f0f2f5")
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=f"系统 #{idx}", bg="#f0f2f5",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL, "bold"),
                 fg="#2c3e50").pack(side=tk.LEFT)

        # ---- 第1行：系统名称 + 系统等级 ----
        ln1 = tk.Frame(row_frame, bg="#f0f2f5")
        ln1.pack(fill=tk.X, pady=(2, 0))
        tk.Label(ln1, text="名称", bg="#f0f2f5",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 fg="#7f8c8d", width=3, anchor="e").pack(side=tk.LEFT)
        sys_var = tk.StringVar(value=data.get("system_name", ""))
        sys_entry, sys_outer = bordered_entry(ln1, textvariable=sys_var, width=22)
        sys_outer.pack(side=tk.LEFT, padx=(2, 8), fill=tk.X, expand=True)
        tk.Label(ln1, text="等级", bg="#f0f2f5",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 fg="#7f8c8d", width=3, anchor="e").pack(side=tk.LEFT)
        lvl_var = tk.StringVar(value=data.get("level", ""))
        lvl_combo = ttk.Combobox(
            ln1, textvariable=lvl_var, values=LEVEL_VALUES,
            state="readonly", width=7,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
        )
        lvl_combo.pack(side=tk.LEFT, padx=(2, 0))

        # ---- 第2行：证书编号 + 下证日期 + 日历按钮 ----
        ln2 = tk.Frame(row_frame, bg="#f0f2f5")
        ln2.pack(fill=tk.X, pady=(2, 0))
        tk.Label(ln2, text="证书", bg="#f0f2f5",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 fg="#7f8c8d", width=3, anchor="e").pack(side=tk.LEFT)
        cert_var = tk.StringVar(value=data.get("cert_number", ""))
        cert_entry, cert_outer = bordered_entry(
            ln2, textvariable=cert_var, width=24,
        )
        cert_outer.pack(side=tk.LEFT, padx=(2, 8))
        tk.Label(ln2, text="下证", bg="#f0f2f5",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 fg="#7f8c8d", width=3, anchor="e").pack(side=tk.LEFT)
        issue_var = tk.StringVar(value=data.get("issue_date", ""))
        issue_entry, issue_outer = bordered_entry(
            ln2, textvariable=issue_var, width=14,
        )
        issue_outer.pack(side=tk.LEFT, padx=(2, 2))
        tk.Button(
            ln2, text="\U0001f4c5",
            command=lambda v=issue_var: self._open_row_issue_calendar(v),
            bg="#f0f2f5", fg="#3498db", relief="flat",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_LARGE),
            cursor="hand2", padx=2, pady=0,
            activebackground="#e0e4e8",
        ).pack(side=tk.LEFT)
        # OCR 识别按钮（每行独立）
        tk.Button(
            ln2, text="OCR", command=lambda ri=idx: self._on_row_upload_cert(ri - 1),
            bg="#27ae60", fg="white", cursor="hand2", relief="flat",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 2),
            padx=4, pady=1, activebackground="#219a52",
        ).pack(side=tk.LEFT, padx=(4, 0))

        # ---- 第3行：属地（省/市） + 复制/删除按钮 ----
        ln3 = tk.Frame(row_frame, bg="#f0f2f5")
        ln3.pack(fill=tk.X, pady=(2, 0))
        tk.Label(ln3, text="属地", bg="#f0f2f5",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
                 fg="#7f8c8d", width=3, anchor="e").pack(side=tk.LEFT)
        prov_var = tk.StringVar(value=data.get("province", ""))
        prov_combo = ttk.Combobox(
            ln3, textvariable=prov_var, values=PROVINCES,
            state="readonly", width=8,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
        )
        prov_combo.pack(side=tk.LEFT, padx=(2, 2))
        init_cities = []
        if data.get("province"):
            init_cities = PROVINCE_CITIES.get(data["province"], [])
        city_var = tk.StringVar(value=data.get("city", ""))
        city_combo = ttk.Combobox(
            ln3, textvariable=city_var,
            values=init_cities if init_cities else ["请先选择省区"],
            state="readonly", width=8,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
        )
        city_combo.pack(side=tk.LEFT)

        # 省级下拉变更时，联动更新市级选项
        prov_combo.bind(
            "<<ComboboxSelected>>",
            lambda e, pc=prov_combo, cc=city_combo: self._on_row_province_change(pc, cc),
        )

        # 将行数据存入集合
        row_data = {
            "frame": row_frame,
            "system_var": sys_var,
            "system_entry": sys_entry,
            "level_var": lvl_var,
            "level_combo": lvl_combo,
            "cert_var": cert_var,
            "cert_entry": cert_entry,
            "issue_date_var": issue_var,
            "issue_date_entry": issue_entry,
            "province_var": prov_var,
            "province_combo": prov_combo,
            "city_var": city_var,
            "city_combo": city_combo,
        }
        self._sys_rows_list.append(row_data)

        # ---- 删除按钮（右对齐） ----
        del_btn = tk.Button(
            ln3, text="删除", command=lambda: self._remove_sys_row(row_data),
            bg="#e74c3c", fg="white", relief="flat", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
            padx=6, pady=0, activebackground="#c0392b",
        )
        del_btn.pack(side=tk.RIGHT)
        row_data["del_btn"] = del_btn  # 存储引用以便后续设置状态

        # ---- 复制按钮 ----
        dup_btn = tk.Button(
            ln3, text="复制", command=lambda: self._dup_sys_row(row_data),
            bg="#ecf0f1", fg="#2c3e50", relief="flat", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
            padx=6, pady=0, activebackground="#d5dbdb",
        )
        dup_btn.pack(side=tk.RIGHT, padx=(0, 3))

        # 如果只剩一行，隐藏删除按钮
        self._refresh_delete_buttons()
        return row_data

    def _remove_sys_row(self, row_data: dict):
        """删除指定系统行（至少保留一行）。

        Args:
            row_data: _add_sys_row 返回的行数据字典。
        """
        if len(self._sys_rows_list) <= 1:
            return  # 至少保留一行
        if row_data in self._sys_rows_list:
            self._sys_rows_list.remove(row_data)
        row_data["frame"].destroy()
        self._refresh_delete_buttons()

    def _dup_sys_row(self, row_data: dict):
        """复制指定系统行的数据并添加为新行。

        Args:
            row_data: 源行数据字典（来自 _add_sys_row）。
        """
        copy_data = {
            "system_name": row_data["system_var"].get(),
            "level": row_data["level_var"].get(),
            "cert_number": row_data["cert_var"].get(),
            "issue_date": row_data["issue_date_var"].get(),
            "province": row_data["province_var"].get(),
            "city": row_data["city_var"].get(),
        }
        self._add_sys_row(copy_data)

    def _on_row_province_change(self, prov_combo, city_combo, keep_city: str = ""):
        """省级下拉变更时更新对应行的市级下拉选项。

        Args:
            prov_combo: 该行的省级 ttk.Combobox 控件。
            city_combo: 该行的市级 ttk.Combobox 控件。
            keep_city: 期望保留选中的市级名称（编辑模式预填时使用）。
        """
        province = prov_combo.get()
        cities = PROVINCE_CITIES.get(province, [])
        if not cities:
            cities = ["请先选择省区"]
        city_combo["values"] = cities
        city_combo.set(keep_city if keep_city in cities else "")

    def _refresh_delete_buttons(self):
        """根据当前行数刷新所有删除按钮的可见性。

        至少保留一行——当只有一行时，隐藏所有删除按钮。
        """
        single = len(self._sys_rows_list) <= 1
        for rd in self._sys_rows_list:
            btn = rd.get("del_btn")
            if btn and btn.winfo_exists():
                btn.pack_forget()
                if not single:
                    btn.pack(side=tk.RIGHT)

    # =========================================================================
    # 数据加载
    # =========================================================================

    def _load_data(self):
        """加载数据到表单字段。

        编辑模式下：将现有项目对象的各属性值填入对应表单控件。
        多系统（_all_projects）时：为每个项目创建一行系统数据。
        新增模式下：将阶段下拉框默认选中第一个阶段。

        最后将输入焦点设置到公司名称输入框，方便用户立即开始输入。
        """
        if self._project:
            # ---- 编辑模式：预填现有项目数据 ----
            self._company_var.set(self._project.company_name)   # 填入公司名称

            # 决定系统行数据来源：优先使用 _all_projects（合并卡片多系统），
            # 否则从单个 _project 提取数据填入第一行
            if self._all_projects and len(self._all_projects) > 1:
                # 清除 _build_form 创建的默认空行
                for rd in list(self._sys_rows_list):
                    rd["frame"].destroy()
                self._sys_rows_list.clear()

                # 为每个项目创建一行
                for p in self._all_projects:
                    prov, city = "", ""
                    if p.location:
                        parts = p.location.rsplit("-", 1)
                        if len(parts) == 2:
                            prov, city = parts[0], parts[1]
                    self._add_sys_row({
                        "system_name": p.system_name,
                        "level": p.level,
                        "cert_number": p.cert_number,
                        "issue_date": p.issue_date,
                        "province": prov,
                        "city": city,
                    })
            else:
                # 单系统：直接填充第一行（_build_form 已创建）
                first = self._sys_rows_list[0]
                first["system_var"].set(self._project.system_name)
                first["cert_var"].set(self._project.cert_number)
                first["issue_date_var"].set(self._project.issue_date)
                if self._project.level:
                    first["level_var"].set(self._project.level)
                if self._project.location:
                    parts = self._project.location.rsplit("-", 1)
                    if len(parts) == 2:
                        first["province_var"].set(parts[0])
                        self._on_row_province_change(
                            first["province_combo"], first["city_combo"],
                            keep_city=parts[1],
                        )

            self._deadline_var.set(self._project.deadline)      # 填入交付日期
            self._folder_path_var.set(self._project.folder_path or "")  # 填入文件夹路径

            # 按 stage_id 匹配并选中对应的阶段下拉项
            for stage in self._stages:
                if stage.id == self._project.stage_id:          # 找到匹配的阶段
                    self._stage_var.set(stage.name)
                    break
            # 如果未匹配到任何阶段且有可用阶段列表，默认选第一个
            if not self._stage_var.get() and self._stages:
                self._stage_combo.current(0)

            # 填入备注内容（从文本框第1行第0列开始插入）
            if self._project.notes:
                self._notes_text.insert("1.0", self._project.notes)
        else:
            # ---- 新增模式：默认选中第一个流程阶段 ----
            if self._stages:
                self._stage_combo.current(0)                    # ComboBox 选中第一项

        # 将输入焦点设置到公司名称输入框，方便用户直接开始输入
        self._company_entry.focus_set()

    # =========================================================================
    # 日历选择器
    # =========================================================================

    def _open_calendar(self):
        """打开日历选择器并填入交付日期输入框。

        以当前交付日期输入框的值作为日历的初始日期；
        若用户在日历中点击了某个日期，则将选中日期写入交付日期字段。
        """
        result = pick_date(self, self._deadline_var.get())   # 弹出日历面板
        if result is not None:
            self._deadline_var.set(result)                   # 将选中日期填入输入框

    def _open_issue_calendar(self):
        """打开日历选择器并填入第一行下证日期输入框（向后兼容）。"""
        if self._sys_rows_list:
            self._open_row_issue_calendar(self._sys_rows_list[0]["issue_date_var"])

    def _open_row_issue_calendar(self, date_var):
        """打开日历选择器并将选中日期填入指定的 StringVar。

        Args:
            date_var: 目标日期的 tk.StringVar 实例。
        """
        result = pick_date(self, date_var.get())
        if result is not None:
            date_var.set(result)

    # =========================================================================
    # 属地联动
    # =========================================================================

    def _on_province_change(self, event=None, keep_city=""):
        """省级下拉变更时的处理函数（向后兼容，操作第一行系统数据）。

        根据选中的省级行政区，更新第一行系统数据的市级下拉选项。
        若传入 keep_city 参数且该市级存在于列表中，则自动选中该市。

        Args:
            event: Tk 事件对象（可为 None）。
            keep_city: 期望保留选中的市级名称（编辑模式预填时使用）。
        """
        if self._sys_rows_list:
            self._on_row_province_change(
                self._sys_rows_list[0]["province_combo"],
                self._sys_rows_list[0]["city_combo"],
                keep_city=keep_city,
            )

    # =========================================================================
    # 快捷日期设置
    # =========================================================================

    def _set_one_week_later(self):
        """将交付日期设置为当前日期的一周后（+7天）。"""
        d = date.today() + timedelta(days=7)                 # 计算 7 天后的日期
        self._deadline_var.set(d.strftime("%Y-%m-%d"))       # 格式化为 YYYY-MM-DD 并设置

    def _set_one_month_later(self):
        """将交付日期设置为当前日期的一个月后（+30天）。"""
        d = date.today() + timedelta(days=30)                # 计算 30 天后的日期
        self._deadline_var.set(d.strftime("%Y-%m-%d"))       # 格式化为 YYYY-MM-DD 并设置

    # =========================================================================
    # 确认与验证
    # =========================================================================

    def _on_confirm(self):
        """确认按钮处理：验证表单输入并收集数据到 self.result。

        验证规则：
          - 多系统表格中至少有一行填写了系统名称（或公司名称非空）。
          - 交付日期如果填写了，必须为合法的 YYYY-MM-DD 格式。
          - 每行的证书编号如果非空，必须符合 "11位数字 - 5位数字" 格式。

        通过验证后，收集所有表单字段到结果字典，包括新增的 "systems" 数组
        和向后兼容的顶层字段（取自第一行系统数据）。
        然后调用 destroy() 关闭对话框。
        """
        # 获取并去除输入字符串的首尾空白字符
        company_name = self._company_var.get().strip()

        # ① 收集所有系统行数据
        systems = []
        for rd in self._sys_rows_list:
            s_name = rd["system_var"].get().strip()
            s_level = rd["level_var"].get().strip()
            s_cert = rd["cert_var"].get().strip()
            s_issue = rd["issue_date_var"].get().strip()
            s_prov = rd["province_var"].get().strip()
            s_city = rd["city_var"].get().strip()
            s_loc = ""
            if s_prov and s_city and s_city != "请先选择省区":
                s_loc = f"{s_prov}-{s_city}"
            systems.append({
                "system_name": s_name,
                "level": s_level,
                "cert_number": s_cert,
                "issue_date": s_issue,
                "location": s_loc,
            })

        # ② 验证：至少有一个系统名称或公司名称
        first_sys_name = systems[0]["system_name"] if systems else ""
        has_system = any(s["system_name"] for s in systems)
        if not company_name and not has_system:
            messagebox.showwarning("输入提示",
                                   "公司名称和系统名称至少填写一个",
                                   parent=self)
            self._company_entry.focus_set()
            return

        # ③ 日期格式验证（仅当填写了交付日期时进行）
        deadline = self._deadline_var.get().strip()
        if deadline:
            try:
                date.fromisoformat(deadline)
            except (ValueError, TypeError):
                messagebox.showwarning("输入提示",
                                       "日期格式不正确，请使用 YYYY-MM-DD 格式",
                                       parent=self)
                return

        # ④ 验证每行的证书编号格式
        for i, s in enumerate(systems):
            if s["cert_number"]:
                valid_cert, cert_msg = validate_cert_number(s["cert_number"])
                if not valid_cert:
                    messagebox.showwarning("输入提示",
                                           f"系统 #{i + 1}：{cert_msg}",
                                           parent=self)
                    return

        # ⑤ 获取阶段 ID：按阶段名称在阶段列表中匹配对应的 ID
        stage_name = self._stage_var.get()
        stage_id = ""
        for s in self._stages:
            if s.name == stage_name:
                stage_id = s.id
                break

        # ⑥ 收集所有表单数据到结果字典（含向后兼容顶层字段）
        self.result = {
            "company_name": company_name,
            "system_name": first_sys_name,
            "cert_number": systems[0]["cert_number"] if systems else "",
            "issue_date": systems[0]["issue_date"] if systems else "",
            "level": systems[0]["level"] if systems else "",
            "location": systems[0]["location"] if systems else "",
            "deadline": deadline,
            "notes": self._notes_text.get("1.0", "end-1c").strip(),
            "stage_id": stage_id,
            "folder_path": self._folder_path_var.get().strip(),
            "systems": systems,
        }
        self.destroy()  # 关闭对话框

    def _get_location(self) -> str:
        """根据省级和市级的当前选择值，拼接属地字符串。

        格式为 "省区-市区"。
        若市级未选择或为占位文字 "请先选择省区"，则返回空字符串。

        Returns:
            str: 形如 "广东-深圳" 的属地字符串，或空字符串。
        """
        p = self._province_var.get().strip()                 # 省级选择值
        c = self._city_var.get().strip()                     # 市级选择值
        # 仅当两级均有有效选择时才拼接返回
        if p and c and c != "请先选择省区" and c != "":
            return f"{p}-{c}"
        return ""

    # =========================================================================
    # 文件/文件夹操作
    # =========================================================================

    def _on_browse_folder(self):
        """打开系统文件夹选择对话框，将选中的路径写入文件夹输入框。

        用户点击"选择"按钮时触发。若用户取消选择（返回空路径），则不更新输入框。
        """
        path = filedialog.askdirectory(parent=self, title="选择项目文件夹")
        if path:
            self._folder_path_var.set(path)                  # 将选中路径填入输入框

    def _on_create_folders(self):
        """在指定路径下创建项目子目录结构。

        创建的目录包括：
          - 01-其他归档文件
          - 00-{公司名}-{系统名}-报告打印
          - 13-{公司名}-{系统名}-渗透测试报告

        使用 os.makedirs 递归创建，exist_ok=True 确保目录已存在时不报错。
        路径中的 / 和 \\ 会被替换为 _ 以避免路径解析错误。
        """
        try:
            root = self._folder_path_var.get().strip()
            if not root:
                messagebox.showwarning("提示", "请先输入或选择文件夹路径", parent=self)
                return
            # 获取公司名称和系统名称，将路径分隔符替换为下划线防止解析问题
            cname = (self._company_var.get().strip() or "未命名").replace("/", "_").replace("\\", "_")
            sname = (self._system_var.get().strip() or "").replace("/", "_").replace("\\", "_")
            # 定义子目录列表
            subdirs = [
                "01-其他归档文件",
                f"00-{cname}-{sname}-报告打印",
                f"13-{cname}-{sname}-渗透测试报告",
            ]
            # 逐个创建子目录
            for d in subdirs:
                os.makedirs(os.path.join(root, d), exist_ok=True)  # 递归创建，已存在则跳过
            messagebox.showinfo("完成", "项目目录结构已创建/刷新", parent=self)
        except OSError as e:
            messagebox.showerror("错误", f"创建失败: {e}", parent=self)

    # =========================================================================
    # OCR 备案证识别（委托到 ui.dialog_project_ocr 中的独立函数）
    # =========================================================================

    def _on_upload_cert(self):
        """上传备案证文件并启动后台线程进行 OCR 识别。（委托）"""
        on_upload_cert(self)

    def _on_row_upload_cert(self, row_idx: int):
        """为指定系统行上传备案证并进行 OCR 识别。"""
        import threading
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            parent=self, title="选择备案证文件",
            filetypes=[("图片和PDF", "*.pdf *.png *.jpg *.jpeg *.bmp")])
        if not file_path:
            return
        self._ocr_status.configure(text="正在识别...", fg="#f39c12")

        def _run():
            try:
                from services.cert_ocr import CertOCRService
                result = CertOCRService().recognize(file_path)
                self.after(0, lambda: self._fill_row_cert_result(result, row_idx, file_path))
            except Exception as e:
                self.after(0, lambda: ocr_failed(self, str(e)))
        threading.Thread(target=_run, daemon=True).start()

    def _fill_row_cert_result(self, result, row_idx, file_path):
        """将 OCR 结果填入指定系统行。"""
        if row_idx < len(self._sys_rows_list):
            r = self._sys_rows_list[row_idx]
            filled = []
            if result.get("company_name"):
                self._company_var.set(result["company_name"]); filled.append("公司名称")
            if result.get("system_name"):
                r["system_var"].set(result["system_name"]); filled.append("系统名称")
            if result.get("cert_number"):
                r["cert_var"].set(result["cert_number"]); filled.append("证书编号")
            if result.get("issue_date"):
                r["issue_date_var"].set(result["issue_date"]); filled.append("下证日期")
            if result.get("level"):
                r["level_var"].set(result["level"]); filled.append("系统等级")
            self._ocr_status.configure(
                text=f"已识别：{'、'.join(filled)}（请核对）" if filled else "识别结果不完整",
                fg="#27ae60" if filled else "#e67e22")
            if file_path and filled:
                archive_cert_file(self, file_path)
        else:
            self._ocr_status.configure(text="识别失败：行索引无效", fg="#e74c3c")

    def _fill_cert_result(self, result: dict, file_path: str = ""):
        """将 OCR 识别结果填充到表单字段。（委托）"""
        fill_cert_result(self, result, file_path)

    def _archive_cert_file(self, src_path: str):
        """将备案证文件复制到项目归档目录。（委托）"""
        archive_cert_file(self, src_path)

    def _ocr_failed(self, error: str):
        """OCR 识别失败处理。（委托）"""
        ocr_failed(self, error)

    # =========================================================================
    # 窗口居中
    # =========================================================================

    def _center_window(self):
        """将对话框相对于其父窗口居中显示。

        计算步骤：
          1. 调用 update_idletasks() 确保组件尺寸已计算完毕。
          2. 获取本窗口和父窗口的宽高及屏幕坐标。
          3. 计算居中后的左上角坐标 (x, y)：
             x = 父窗口左上角 X + (父宽 - 本宽) / 2
             y = 父窗口左上角 Y + (父高 - 本高) / 2
          4. 调用 geometry() 设置窗口位置。
        """
        self.update_idletasks()                              # 等待所有待处理任务完成，获取准确尺寸
        w = self.winfo_width()                               # 本窗口宽度（像素）
        h = self.winfo_height()                              # 本窗口高度（像素）
        pw = self.master.winfo_width()                       # 父窗口宽度
        ph = self.master.winfo_height()                      # 父窗口高度
        px = self.master.winfo_rootx()                       # 父窗口左上角屏幕 X 坐标
        py = self.master.winfo_rooty()                       # 父窗口左上角屏幕 Y 坐标
        x = px + (pw - w) // 2                               # 计算居中 X 坐标
        y = py + (ph - h) // 2                               # 计算居中 Y 坐标
        self.geometry(f"+{x}+{y}")                           # 设置窗口位置


# =============================================================================
# show_project_dialog -- 便捷函数
# =============================================================================

def show_project_dialog(parent, title: str = "新增项目",
                        project: Project = None,
                        stages: list[WorkflowStage] = None,
                        all_projects: list = None) -> dict | None:
    """显示项目编辑对话框并返回用户输入结果。

    这是外部调用项目对话框的推荐方式。函数内部创建 ProjectDialog 实例，
    使用 parent.wait_window() 阻塞等待对话框关闭，然后返回结果。

    Args:
        parent: 父级窗口（Tk 根窗口或 MainWindow 实例）。
        title: 对话框标题。新增时使用 "新增项目"，编辑时使用 "编辑项目"。
        project: 编辑模式下传入现有项目对象；新增模式下传入 None。
        stages: 流程阶段列表，用于阶段下拉选择。

    Returns:
        dict | None:
            用户点击"保存"后返回包含所有表单字段的字典（详见 ProjectDialog.result）。
            用户点击"取消"或关闭窗口返回 None。
    """
    dialog = ProjectDialog(parent, title, project, stages, all_projects=all_projects)
    parent.wait_window(dialog)                               # 阻塞等待对话框关闭
    return dialog.result                                     # 返回用户操作结果
