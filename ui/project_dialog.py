"""
项目编辑对话框模块 -- 等保测评进度管理系统

本模块提供项目的新增与编辑功能，以模态对话框形式与用户交互。
主要功能包括：
  - 项目基本信息录入（公司名称、系统名称、系统等级、证书编号、属地等）
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
        ...
"""

# =============================================================================
# 标准库导入
# =============================================================================
import os                       # 操作系统接口：创建目录、路径分隔符替换
import threading                # 多线程：后台执行 OCR 识别，避免阻塞 UI 线程
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


# =============================================================================
# 全国省市区静态数据（省级 → 市级列表）
# =============================================================================
# 用于项目属地下拉选择，实现省-市两级联动。
# 键为省级行政区名称，值为该省区下属市级行政区名称列表。
PROVINCE_CITIES = {
    "北京": ["东城区", "西城区", "朝阳区", "丰台区", "石景山区", "海淀区", "顺义区", "通州区", "大兴区", "房山区", "昌平区", "怀柔区", "密云区", "延庆区", "平谷区", "门头沟区"],
    "天津": ["和平区", "河东区", "河西区", "南开区", "河北区", "红桥区", "东丽区", "西青区", "北辰区", "武清区", "宝坻区", "滨海新区", "宁河区", "静海区", "蓟州区"],
    "上海": ["黄浦区", "徐汇区", "长宁区", "静安区", "普陀区", "虹口区", "杨浦区", "闵行区", "宝山区", "嘉定区", "浦东新区", "金山区", "松江区", "青浦区", "奉贤区", "崇明区"],
    "重庆": ["渝中区", "江北区", "南岸区", "沙坪坝区", "九龙坡区", "大渡口区", "北碚区", "渝北区", "巴南区", "万州区", "涪陵区", "黔江区", "长寿区", "江津区", "合川区", "永川区"],
    "河北": ["石家庄", "唐山", "秦皇岛", "邯郸", "邢台", "保定", "张家口", "承德", "沧州", "廊坊", "衡水"],
    "山西": ["太原", "大同", "阳泉", "长治", "晋城", "朔州", "晋中", "运城", "忻州", "临汾", "吕梁"],
    "内蒙古": ["呼和浩特", "包头", "乌海", "赤峰", "通辽", "鄂尔多斯", "呼伦贝尔", "巴彦淖尔", "乌兰察布", "兴安盟", "锡林郭勒盟", "阿拉善盟"],
    "辽宁": ["沈阳", "大连", "鞍山", "抚顺", "本溪", "丹东", "锦州", "营口", "阜新", "辽阳", "盘锦", "铁岭", "朝阳", "葫芦岛"],
    "吉林": ["长春", "吉林", "四平", "辽源", "通化", "白山", "松原", "白城", "延边"],
    "黑龙江": ["哈尔滨", "齐齐哈尔", "鸡西", "鹤岗", "双鸭山", "大庆", "伊春", "佳木斯", "七台河", "牡丹江", "黑河", "绥化", "大兴安岭"],
    "江苏": ["南京", "无锡", "徐州", "常州", "苏州", "南通", "连云港", "淮安", "盐城", "扬州", "镇江", "泰州", "宿迁"],
    "浙江": ["杭州", "宁波", "温州", "嘉兴", "湖州", "绍兴", "金华", "衢州", "舟山", "台州", "丽水"],
    "安徽": ["合肥", "芜湖", "蚌埠", "淮南", "马鞍山", "淮北", "铜陵", "安庆", "黄山", "滁州", "阜阳", "宿州", "六安", "亳州", "池州", "宣城"],
    "福建": ["福州", "厦门", "莆田", "三明", "泉州", "漳州", "南平", "龙岩", "宁德"],
    "江西": ["南昌", "景德镇", "萍乡", "九江", "新余", "鹰潭", "赣州", "吉安", "宜春", "抚州", "上饶"],
    "山东": ["济南", "青岛", "淄博", "枣庄", "东营", "烟台", "潍坊", "济宁", "泰安", "威海", "日照", "临沂", "德州", "聊城", "滨州", "菏泽"],
    "河南": ["郑州", "开封", "洛阳", "平顶山", "安阳", "鹤壁", "新乡", "焦作", "濮阳", "许昌", "漯河", "三门峡", "南阳", "商丘", "信阳", "周口", "驻马店", "济源"],
    "湖北": ["武汉", "黄石", "十堰", "宜昌", "襄阳", "鄂州", "荆门", "孝感", "荆州", "黄冈", "咸宁", "随州", "恩施", "仙桃", "潜江", "天门", "神农架"],
    "湖南": ["长沙", "株洲", "湘潭", "衡阳", "邵阳", "岳阳", "常德", "张家界", "益阳", "郴州", "永州", "怀化", "娄底", "湘西"],
    "广东": ["广州", "韶关", "深圳", "珠海", "汕头", "佛山", "江门", "湛江", "茂名", "肇庆", "惠州", "梅州", "汕尾", "河源", "阳江", "清远", "东莞", "中山", "潮州", "揭阳", "云浮"],
    "广西": ["南宁", "柳州", "桂林", "梧州", "北海", "防城港", "钦州", "贵港", "玉林", "百色", "贺州", "河池", "来宾", "崇左"],
    "海南": ["海口", "三亚", "三沙", "儋州", "五指山", "琼海", "文昌", "万宁", "东方", "定安", "屯昌", "澄迈", "临高", "白沙", "昌江", "乐东", "陵水", "保亭", "琼中"],
    "四川": ["成都", "自贡", "攀枝花", "泸州", "德阳", "绵阳", "广元", "遂宁", "内江", "乐山", "南充", "眉山", "宜宾", "广安", "达州", "雅安", "巴中", "资阳", "阿坝", "甘孜", "凉山"],
    "贵州": ["贵阳", "六盘水", "遵义", "安顺", "毕节", "铜仁", "黔西南", "黔东南", "黔南"],
    "云南": ["昆明", "曲靖", "玉溪", "保山", "昭通", "丽江", "普洱", "临沧", "楚雄", "红河", "文山", "西双版纳", "大理", "德宏", "怒江", "迪庆"],
    "西藏": ["拉萨", "日喀则", "昌都", "林芝", "山南", "那曲", "阿里"],
    "陕西": ["西安", "铜川", "宝鸡", "咸阳", "渭南", "延安", "汉中", "榆林", "安康", "商洛", "杨凌"],
    "甘肃": ["兰州", "嘉峪关", "金昌", "白银", "天水", "武威", "张掖", "平凉", "酒泉", "庆阳", "定西", "陇南", "临夏", "甘南"],
    "青海": ["西宁", "海东", "海北", "黄南", "海南", "果洛", "玉树", "海西"],
    "宁夏": ["银川", "石嘴山", "吴忠", "固原", "中卫"],
    "新疆": ["乌鲁木齐", "克拉玛依", "吐鲁番", "哈密", "昌吉", "博尔塔拉", "巴音郭楞", "阿克苏", "克孜勒苏", "喀什", "和田", "伊犁", "塔城", "阿勒泰", "石河子"],
    "香港": ["中西区", "湾仔区", "东区", "南区", "油尖旺区", "深水埗区", "九龙城区", "黄大仙区", "观塘区", "荃湾区", "屯门区", "元朗区", "北区", "大埔区", "沙田区", "西贡区", "离岛区"],
    "澳门": ["花地玛堂区", "圣安多尼堂区", "大堂区", "望德堂区", "风顺堂区", "嘉模堂区", "圣方济各堂区"],
    "台湾": ["台北", "高雄", "台中", "台南", "基隆", "新竹", "嘉义", "桃园", "新北"],
}
# 省级行政区名称列表（提取 PROVINCE_CITIES 的所有键），供省级下拉选择框使用
PROVINCES = list(PROVINCE_CITIES.keys())


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
      2. 系统名称
      3. 系统等级（下拉选择：空/第一至第五级）
      4. 证书编号（11位数字 - 5位数字格式校验）
      5. 下证日期（日历选择器）+ 属地（省-市两级联动下拉）
      6. 上传备案证识别按钮（OCR 自动填充）
      7. 交付日期（日历选择器 + 今天/一周后/一月后/清除快捷按钮）
      8. 所属阶段（只读下拉选择）
      9. 项目文件夹（路径选择 + 创建目录按钮）
      10. 备注信息（多行文本，带滚动条和灰色外边框）

    键盘快捷键：
      - Enter：确认保存
      - Esc：取消关闭

    Attributes:
        result: dict | None
            用户确认保存后为包含所有表单字段的字典，取消时为 None。
            字典字段：company_name, system_name, cert_number, issue_date,
            level, location, deadline, notes, stage_id, folder_path
    """

    def __init__(self, parent, title: str = "新增项目",
                 project: Project = None,
                 stages: list[WorkflowStage] = None):
        """初始化项目新增/编辑对话框。

        Args:
            parent: 父级窗口（通常为 Tk 根窗口或 MainWindow 实例）。
            title: 对话框标题字符串。新增时默认为 "新增项目"，编辑时传入 "编辑项目"。
            project: 待编辑的现有项目对象。为 None 表示新增模式，非空表示编辑模式。
            stages: 流程阶段列表。用于填充阶段下拉选择框。默认空列表。
        """
        # 调用父类 Tk.Toplevel 构造器，创建独立顶层窗口
        super().__init__(parent)
        # 设置对话框标题
        self.title(title)
        # 初始化结果变量：None 表示用户取消，确认后将被赋值为表单数据字典
        self.result = None
        # 保存待编辑的项目对象引用（编辑模式使用；新增模式为 None）
        self._project = project
        # 保存流程阶段列表（若未传入则使用空列表兜底）
        self._stages = stages or []
        # 判断当前是否为编辑模式（project 非空则为编辑，否则为新增）
        self._is_edit = project is not None

        # ---- 按顺序执行窗口初始化步骤 ----
        self._setup_window()     # ① 配置窗口基本属性（大小、最小尺寸、背景色）
        self._build_form()       # ② 构建表单 UI 布局（所有控件和容器）
        self._load_data()        # ③ 编辑模式下预填数据，或设置新增模式的默认值
        self._center_window()    # ④ 将窗口相对于父窗口居中显示
        self.grab_set()          # ⑤ 设置模态（拦截所有事件，必须关闭本窗口后才能操作父窗口）

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
        self.geometry("540x620")         # 设置窗口初始宽度540px，高度620px
        self.minsize(420, 480)           # 设置窗口最小宽度420px，最小高度480px
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
             - 系统名称输入框
             - 系统等级下拉框
             - 证书编号输入框
             - 下证日期（日历按钮）+ 属地（省-市联动下拉）-- 左右分栏
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
                          ├── 各种表单字段控件 ...
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
                 ).pack(anchor="w", pady=(0, 15))

        # =====================================================================
        # 1. 公司名称（必填字段，红色星号 * 标记）
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
        # 2. 系统名称
        # =====================================================================
        tk.Label(main_frame, text="系统名称", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        self._system_var = tk.StringVar()             # 系统名称的 StringVar 变量
        self._system_entry, s_outer = bordered_entry(
            main_frame, textvariable=self._system_var,
        )
        s_outer.pack(fill=tk.X, pady=(2, 5))

        # =====================================================================
        # 3. 系统等级（下拉选择，只读）
        # =====================================================================
        tk.Label(main_frame, text="系统等级", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        self._level_var = tk.StringVar()              # 系统等级的 StringVar 变量
        level_values = ["", "第一级", "第二级", "第三级", "第四级", "第五级"]  # 下拉选项列表
        self._level_combo = ttk.Combobox(
            main_frame, textvariable=self._level_var,
            values=level_values, state="readonly",    # 只读下拉框，禁止用户手动输入
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
        )
        self._level_combo.pack(fill=tk.X, pady=(2, 5))

        # =====================================================================
        # 4. 证书编号
        # =====================================================================
        tk.Label(main_frame, text="证书编号", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        self._cert_var = tk.StringVar()               # 证书编号的 StringVar 变量
        self._cert_entry, f_outer = bordered_entry(
            main_frame, textvariable=self._cert_var,
        )
        f_outer.pack(fill=tk.X, pady=(2, 5))

        # =====================================================================
        # 5. 下证日期 + 属地（左右分栏布局）
        # =====================================================================
        row5 = tk.Frame(main_frame, bg="#ffffff")     # 整体行容器
        row5.pack(fill=tk.X, pady=(2, 5))

        # --- 下证日期（左侧列）---
        issue_col = tk.Frame(row5, bg="#ffffff")
        issue_col.pack(side=tk.LEFT)
        tk.Label(issue_col, text="下证日期", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        issue_input_row = tk.Frame(issue_col, bg="#ffffff")
        issue_input_row.pack(fill=tk.X, pady=(2, 0))
        self._issue_date_var = tk.StringVar()           # 下证日期的 StringVar 变量
        self._issue_date_entry, id_outer = bordered_entry(
            issue_input_row, textvariable=self._issue_date_var, width=18,
        )
        id_outer.pack(side=tk.LEFT)
        # 日历按钮，点击弹出日历选择器
        tk.Button(
            issue_input_row, text="\U0001f4c5", command=self._open_issue_calendar,
            bg="#ffffff", fg="#3498db", relief="flat",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_LARGE),
            cursor="hand2", padx=3, pady=0,
            activebackground="#ecf0f1",
        ).pack(side=tk.LEFT, padx=(2, 0))

        # --- 属地（右侧列，省级 + 市级两级联动下拉）---
        loc_col = tk.Frame(row5, bg="#ffffff")
        loc_col.pack(side=tk.LEFT, padx=(20, 0))
        tk.Label(loc_col, text="属地", bg="#ffffff",
                 font=(Config.FONT_FAMILY, Config.FONT_SIZE_NORMAL),
                 ).pack(anchor="w")
        loc_input_row = tk.Frame(loc_col, bg="#ffffff")
        loc_input_row.pack(fill=tk.X, pady=(2, 0))
        # 省级下拉框
        self._province_var = tk.StringVar()
        self._province_combo = ttk.Combobox(
            loc_input_row, textvariable=self._province_var, values=PROVINCES,
            state="readonly", width=8,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
        )
        self._province_combo.pack(side=tk.LEFT, padx=(0, 2))
        # 省级下拉变更时更新市级下拉选项
        self._province_combo.bind("<<ComboboxSelected>>", self._on_province_change)
        # 市级下拉框
        self._city_var = tk.StringVar()
        self._city_combo = ttk.Combobox(
            loc_input_row, textvariable=self._city_var, values=["请先选择省区"],
            state="readonly", width=10,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
        )
        self._city_combo.pack(side=tk.LEFT)
        self._city_combo.set("请先选择省区")            # 初始默认提示文字

        # =====================================================================
        # 上传备案证识别按钮 + OCR 状态标签
        # =====================================================================
        upload_row = tk.Frame(main_frame, bg="#ffffff")
        upload_row.pack(fill=tk.X, pady=(0, 5))
        self._upload_btn = tk.Button(
            upload_row, text="上传备案证识别", command=self._on_upload_cert,
            bg="#27ae60", fg="white", cursor="hand2",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL),
            relief="flat", padx=10, pady=3,
            activebackground="#219a52",
        )
        self._upload_btn.pack(side=tk.LEFT)
        # OCR 识别状态提示标签（初始为空）
        self._ocr_status = tk.Label(upload_row, text="", bg="#ffffff",
                                     font=(Config.FONT_FAMILY, Config.FONT_SIZE_SMALL - 1),
                                     fg="#7f8c8d")
        self._ocr_status.pack(side=tk.LEFT, padx=(10, 0))

        # =====================================================================
        # 6. 交付日期（日历选择器 + 快捷日期按钮）
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
        # 7. 所属阶段（只读下拉选择）
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
        # 8. 项目文件夹管理（路径输入 + 浏览 + 创建目录）
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
        # 9. 备注信息（多行文本输入，带滚动条和灰色外边框）
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
    # 数据加载
    # =========================================================================

    def _load_data(self):
        """加载数据到表单字段。

        编辑模式下：将现有项目对象的各属性值填入对应表单控件。
        新增模式下：将阶段下拉框默认选中第一个阶段。

        最后将输入焦点设置到公司名称输入框，方便用户立即开始输入。
        """
        if self._project:
            # ---- 编辑模式：预填现有项目数据 ----
            self._company_var.set(self._project.company_name)   # 填入公司名称
            self._system_var.set(self._project.system_name)     # 填入系统名称
            self._cert_var.set(self._project.cert_number)       # 填入证书编号
            self._issue_date_var.set(self._project.issue_date)  # 填入下证日期
            if self._project.level:                              # 填入系统等级（非空时）
                self._level_var.set(self._project.level)
            # 属地数据：格式为 "省区-市区"，按 "-" 拆分并分别设置省级和市级下拉
            if self._project.location:
                parts = self._project.location.rsplit("-", 1)   # 从右侧按第一个 "-" 分割
                if len(parts) == 2:
                    self._province_var.set(parts[0])            # 设置省级
                    self._on_province_change(keep_city=parts[1]) # 加载市级选项并选中
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
        """打开日历选择器并填入下证日期输入框。

        以下证日期输入框的当前值作为日历的初始日期；
        若用户选中了日期则写入下证日期字段。
        """
        result = pick_date(self, self._issue_date_var.get()) # 弹出日历面板
        if result is not None:
            self._issue_date_var.set(result)                 # 将选中日期填入输入框

    # =========================================================================
    # 属地联动
    # =========================================================================

    def _on_province_change(self, event=None, keep_city=""):
        """省级下拉变更时的处理函数：更新市级下拉选项列表。

        根据选中的省级行政区，从 PROVINCE_CITIES 查询对应的市级列表，
        并更新市级下拉框。若传入 keep_city 参数且该市级存在于列表中，
        则自动选中该市。

        Args:
            event: Tk 事件对象（绑定 <<ComboboxSelected>> 时传入），可为 None。
            keep_city: 期望保留选中的市级名称（编辑模式预填时使用）。
        """
        province = self._province_var.get()                  # 获取当前选中的省级名称
        cities = PROVINCE_CITIES.get(province, [])           # 查询对应的市级列表
        if not cities:
            cities = ["请先选择省区"]                         # 无匹配时给出占位提示
        self._city_combo["values"] = cities                  # 更新市级下拉框的选项列表
        # 如果 keep_city 在市级列表中则选中它，否则清空
        self._city_combo.set(keep_city if keep_city in cities else "")

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
          - 公司名称和系统名称至少需要填写一个。
          - 交付日期如果填写了，必须为合法的 YYYY-MM-DD 格式。
          - 证书编号如果非空，必须符合 "11位数字 - 5位数字" 格式。

        通过验证后，将所有表单字段的值收集到一个字典中，赋值给 self.result，
        然后调用 destroy() 关闭对话框。
        """
        # 获取并去除输入字符串的首尾空白字符
        company_name = self._company_var.get().strip()
        system_name = self._system_var.get().strip()

        # ① 验证：公司名称和系统名称至少填写一个
        if not company_name and not system_name:
            messagebox.showwarning("输入提示", "公司名称和系统名称至少填写一个",
                                   parent=self)
            self._company_entry.focus_set()                  # 焦点回到公司名称输入框
            return

        # ② 日期格式验证（仅当填写了交付日期时进行）
        deadline = self._deadline_var.get().strip()
        if deadline:
            try:
                date.fromisoformat(deadline)                 # 尝试解析日期，无效则抛异常
            except (ValueError, TypeError):
                messagebox.showwarning("输入提示",
                                       "日期格式不正确，请使用 YYYY-MM-DD 格式",
                                       parent=self)
                return

        # ③ 证书编号格式验证（非空时须符合 11位数字-5位数字 格式）
        cert_number = self._cert_var.get().strip()
        valid_cert, cert_msg = validate_cert_number(cert_number)
        if not valid_cert:
            messagebox.showwarning("输入提示", cert_msg, parent=self)
            return

        # ④ 获取阶段 ID：按阶段名称在阶段列表中匹配对应的 ID
        stage_name = self._stage_var.get()
        stage_id = ""
        for s in self._stages:
            if s.name == stage_name:
                stage_id = s.id                            # 找到匹配的阶段 ID
                break

        # ⑤ 收集所有表单数据到结果字典
        self.result = {
            "company_name": company_name,                    # 公司名称
            "system_name": system_name,                      # 系统名称
            "cert_number": cert_number,                      # 证书编号
            "issue_date": self._issue_date_var.get().strip(),# 下证日期
            "level": self._level_var.get().strip(),          # 系统等级
            "location": self._get_location(),                # 属地（省-市格式）
            "deadline": deadline,                            # 交付日期
            "notes": self._notes_text.get("1.0", "end-1c").strip(),  # 备注内容
            "stage_id": stage_id,                            # 阶段 ID
            "folder_path": self._folder_path_var.get().strip(), # 项目文件夹路径
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
    # OCR 备案证识别
    # =========================================================================

    def _on_upload_cert(self):
        """上传备案证文件并启动后台线程进行 OCR 识别。

        打开文件选择对话框让用户选择备案证图片或 PDF 文件，
        选中后在后台线程中调用 CertOCRService 进行识别，
        识别结果通过 after 回调回主线程更新表单字段。

        支持的文件格式：PDF、PNG、JPG、JPEG、BMP。
        """
        # 打开文件选择对话框，筛选图片和 PDF 文件
        file_path = filedialog.askopenfilename(
            parent=self,
            title="选择备案证文件",
            filetypes=[
                ("图片和PDF文件", "*.pdf *.png *.jpg *.jpeg *.bmp"),
                ("PDF文件", "*.pdf"),
                ("图片文件", "*.png *.jpg *.jpeg *.bmp"),
            ],
        )
        if not file_path:
            return  # 用户取消选择，直接返回

        # 禁用上传按钮并显示识别中状态
        self._upload_btn.configure(state="disabled", text="识别中...")
        self._ocr_status.configure(text="正在识别备案证，请稍候...", fg="#f39c12")

        def _run():
            """后台线程执行函数：调用 OCR 服务并回传结果到主线程。"""
            try:
                from services.cert_ocr import CertOCRService
                result = CertOCRService().recognize(file_path)
                self.after(0, lambda: self._fill_cert_result(result, file_path))
            except Exception as e:
                self.after(0, lambda: self._ocr_failed(str(e)))

        # 启动后台线程执行识别（daemon 线程，随主程序退出自动终止）
        threading.Thread(target=_run, daemon=True).start()

    def _fill_cert_result(self, result: dict, file_path: str = ""):
        """将 OCR 识别结果填充到表单字段，并将备案证文件归档。

        恢复上传按钮，更新各输入框，并将原始文件复制到
        01-其他归档文件/01-备案证-往期测评报告/ 目录下。

        Args:
            result: OCR 识别结果字典，可能包含的键：
                company_name, system_name, cert_number, issue_date, level
        """
        self._upload_btn.configure(state="normal", text="上传备案证识别")  # 恢复按钮
        # 如果识别结果所有值都为空，提示用户手动填写
        if not any(result.values()):
            self._ocr_status.configure(text="未识别到有效信息，请手动填写", fg="#e74c3c")
            return

        # 逐个字段填充到对应输入框，并记录已填充的字段名
        filled = []
        if result.get("company_name"):
            self._company_var.set(result["company_name"]); filled.append("公司名称")
        if result.get("system_name"):
            self._system_var.set(result["system_name"]); filled.append("系统名称")
        if result.get("cert_number"):
            self._cert_var.set(result["cert_number"]); filled.append("证书编号")
        if result.get("issue_date"):
            self._issue_date_var.set(result["issue_date"]); filled.append("下证日期")
        if result.get("level"):
            self._level_var.set(result["level"]); filled.append("系统等级")

        # 更新 OCR 状态标签
        self._ocr_status.configure(
            text=f"已识别：{'、'.join(filled)}（请核对）" if filled else "识别结果不完整",
            fg="#27ae60" if filled else "#e67e22",
        )

        # 归档备案证文件到项目文件夹
        if file_path and filled:
            self._archive_cert_file(file_path)

    def _archive_cert_file(self, src_path: str):
        """将备案证文件复制到项目归档目录。

        目标路径: {项目文件夹}/01-其他归档文件/01-备案证-往期测评报告/
        文件命名: {公司名称}-{系统名称}-备案证.{原扩展名}
        """
        import os, shutil
        try:
            root = self._folder_path_var.get().strip()
            if not root or not os.path.isdir(root):
                return  # 项目文件夹未设置或不存在，跳过归档
            cname = self._company_var.get().strip()
            sname = self._system_var.get().strip()
            if not cname and not sname:
                return  # 无公司/系统名称，跳过
            ext = os.path.splitext(src_path)[1] or ".pdf"
            safe_name = f"{cname or '未知'}-{sname or '未知'}-备案证{ext}"
            safe_name = safe_name.replace("/", "_").replace("\\", "_").replace(":", "_")
            dest_dir = os.path.join(root, "01-其他归档文件", "01-备案证-往期测评报告")
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, safe_name)
            if not os.path.exists(dest_path):
                shutil.copy2(src_path, dest_path)
        except OSError:
            pass  # 归档失败不影响主流程

    def _ocr_failed(self, error: str):
        """OCR 识别失败时的处理：恢复按钮状态并显示错误信息。

        Args:
            error: 错误描述字符串。
        """
        self._upload_btn.configure(state="normal", text="上传备案证识别")  # 恢复按钮
        self._ocr_status.configure(text=f"识别失败：{error}", fg="#e74c3c")  # 显示红色错误信息

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
                        stages: list[WorkflowStage] = None) -> dict | None:
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
    dialog = ProjectDialog(parent, title, project, stages)   # 创建对话框实例
    parent.wait_window(dialog)                               # 阻塞等待对话框关闭
    return dialog.result                                     # 返回用户操作结果
