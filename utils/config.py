"""
配置模块 - 管理应用程序的所有常量配置和默认值

提供：
- 文件路径配置（数据文件、日志文件等）
- 默认流程步骤定义
- UI颜色和样式常量
- 应用程序元数据
"""

import os  # 操作系统接口模块，用于路径拼接和目录操作
import sys  # 系统相关模块，用于判断是否为打包后的可执行文件环境


class Config:
    """应用程序全局配置类
    所有配置项以类变量和类方法的形式组织，无需实例化即可使用
    """

    # ==================== 应用程序元数据 ====================
    APP_NAME = "项目进度管理系统"  # 应用程序显示名称
    APP_VERSION = "2.2.3"               # 当前版本号
    APP_AUTHOR = "网络安全测评团队"       # 开发/维护团队名称

    # ==================== 文件路径配置 ====================
    @staticmethod
    def get_data_dir():
        """获取数据文件存储目录
        使用用户 AppData 目录，确保 EXE 更新后数据不丢失
        """
        if getattr(sys, 'frozen', False):  # 检查是否在 PyInstaller 等打包环境中运行
            # 优先使用 EXE 同目录的 data 文件夹（便携模式）
            exe_dir = os.path.dirname(sys.executable)
            portable_data = os.path.join(exe_dir, "data")
            if os.path.exists(portable_data):
                return exe_dir
            # 回退到用户 AppData 目录（EXE 更新也不会丢失）
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
            base_dir = os.path.join(appdata, "等保测评进度管理系统")
            return base_dir
        else:
            # 源码运行：使用项目根目录
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            return base_dir

    @classmethod
    def get_data_file_path(cls):
        """获取主数据文件完整路径"""
        return os.path.join(cls.get_data_dir(), "data", "dap_data.json")  # 拼接 data/dap_data.json 完整路径

    @classmethod
    def get_log_file_path(cls):
        """获取操作日志文件路径"""
        return os.path.join(cls.get_data_dir(), "data", "operation_log.json")  # 拼接 data/operation_log.json 完整路径

    # ==================== 默认流程步骤 ====================
    DEFAULT_WORKFLOW_STAGES = [
        # 等保测评标准流程的8个阶段，每个阶段包含唯一ID、显示名称、排序序号和主题颜色
        {"id": "stage_1", "name": "项目启动", "order": 0, "color": "#3498db"},  # 蓝色 - 第一步：项目启动
        {"id": "stage_2", "name": "现状调研", "order": 1, "color": "#2ecc71"},  # 绿色 - 第二步：现状调研
        {"id": "stage_3", "name": "差距评估", "order": 2, "color": "#e67e22"},  # 橙色 - 第三步：差距评估
        {"id": "stage_4", "name": "方案设计", "order": 3, "color": "#9b59b6"},  # 紫色 - 第四步：方案设计
        {"id": "stage_5", "name": "整改实施", "order": 4, "color": "#e74c3c"},  # 红色 - 第五步：整改实施
        {"id": "stage_6", "name": "测评验收", "order": 5, "color": "#1abc9c"},  # 青色 - 第六步：测评验收
        {"id": "stage_7", "name": "报告输出", "order": 6, "color": "#f39c12"},  # 黄色 - 第七步：报告输出
        {"id": "stage_8", "name": "项目归档", "order": 7, "color": "#95a5a6"},  # 灰色 - 第八步：项目归档
    ]

    # ==================== UI样式配置 ====================
    # 看板颜色 - 控制看板界面各组件的背景和边框颜色
    KANBAN_BG = "#f0f2f5"           # 看板整体背景色（浅灰蓝）
    COLUMN_BG = "#e8eaed"           # 单列背景色（浅灰）
    COLUMN_HEADER_BG = "#dfe1e6"    # 列标题背景色（略深灰）
    CARD_BG = "#ffffff"             # 卡片背景色（白色）
    CARD_BORDER = "#d0d5dd"         # 卡片边框颜色（浅灰）
    CARD_HOVER_BG = "#f8f9fa"       # 鼠标悬停时卡片背景色（极浅灰）

    # 字体配置 - 统一界面的字体族和字号规格
    FONT_FAMILY = "Microsoft YaHei"  # 默认字体族（微软雅黑，适合中文显示）
    FONT_SIZE_SMALL = 9               # 小字号（用于辅助信息）
    FONT_SIZE_NORMAL = 10             # 正常字号（用于正文内容）
    FONT_SIZE_LARGE = 12              # 大字号（用于标题）
    FONT_SIZE_TITLE = 14              # 标题字号
    FONT_SIZE_HEADER = 16             # 页头字号

    # 窗口默认大小
    WINDOW_WIDTH = 1500  # 主窗口默认宽度（像素）
    WINDOW_HEIGHT = 850  # 主窗口默认高度（像素）
    WINDOW_MIN_WIDTH = 900   # 主窗口最小宽度（防止缩得过小导致布局错乱）
    WINDOW_MIN_HEIGHT = 500  # 主窗口最小高度

    # 卡片尺寸
    CARD_WIDTH = 200       # 每个项目卡片的固定宽度（像素）
    CARD_MIN_HEIGHT = 80   # 每个项目卡片的最小高度（像素）

    # 列尺寸
    COLUMN_WIDTH = 220        # 每个阶段列的固定宽度（像素）
    COLUMN_MIN_HEIGHT = 400   # 每个阶段列的最小高度（像素）

    # 工具栏高度
    TOOLBAR_HEIGHT = 45  # 顶部工具栏的高度（像素）

    # ==================== 日期格式 ====================
    DATE_FORMAT = "%Y-%m-%d"                  # 日期显示格式（年-月-日）
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"     # 日期时间显示格式（年-月-日 时:分:秒）

    # ==================== 状态颜色映射 ====================
    STATUS_COLORS = {
        "normal": "#ffffff",      # 正常状态：白色背景
        "warning": "#fff3cd",     # 即将到期（7天内）：浅黄色背景，起警示作用
        "overdue": "#f8d7da",     # 已超期：浅红色背景，表示严重逾期
        "completed": "#d4edda",   # 已完成（归档阶段）：浅绿色背景，表示已完成
    }

    # 截止日期预警天数
    DEADLINE_WARNING_DAYS = 7  # 截止日期前多少天开始显示黄色预警
