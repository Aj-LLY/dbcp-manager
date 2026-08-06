"""
配置模块 - 管理应用程序的所有常量配置和默认值

本模块定义应用程序的全局配置类 Config，所有配置项以静态方法和类变量的形式组织，
无需实例化即可通过 Config.XXX 直接访问。

配置分类：
  1. 应用程序元数据：名称、版本、作者
  2. 文件路径配置：数据文件、日志文件、配置文件路径（支持打包和源码运行两种模式）
  3. 默认流程步骤：8 个等保测评标准流程阶段的默认定义
  4. UI 样式配置：看板颜色、卡片颜色、字体、窗口尺寸等
  5. 日期格式：用于格式化和显示的标准日期/时间格式
  6. 状态颜色映射：不同项目状态对应的卡片背景色
  7. 业务配置：截止日期预警天数

路径策略（get_data_dir）：
  - PyInstaller 打包运行（sys.frozen = True）：
      1. 优先使用 EXE 同目录的 data 文件夹（便携模式）
      2. 回退到用户 AppData 目录（防止 EXE 更新导致数据丢失）
  - 源码运行（sys.frozen = False）：
      使用项目源码根目录（main.py 所在目录的上级）
"""

# =============================================================================
# 导入区
# =============================================================================

import os  # 操作系统接口模块，用于路径拼接、目录检查和环境变量读取
import sys  # 系统相关模块，用于判断是否为 PyInstaller 打包后的可执行文件环境


class Config:
    """应用程序全局配置类

    所有配置项以类变量（直接访问）和类方法（@classmethod / @staticmethod）的形式组织。
    纯静态设计，无需创建实例即可使用，例如：
      - Config.APP_NAME       # 获取应用名称
      - Config.get_data_dir() # 获取数据目录路径
    """

    # =============================================================================
    # 应用程序元数据
    # =============================================================================

    APP_NAME = "项目进度管理系统"  # 应用程序在产品界面和打包名称中的显示名称
    APP_VERSION = "4.5.2"         # 当前版本号（语义化版本格式：主.次.修订）
    APP_AUTHOR = "网络安全测评团队"  # 开发/维护团队名称（用于打包元数据）

    # =============================================================================
    # 文件路径配置
    # =============================================================================

    @staticmethod
    def get_data_dir():
        """获取数据文件存储目录

        根据运行模式返回不同的数据目录路径：

        打包运行模式（sys.frozen = True）：
          1. 优先检查 EXE 同目录下是否存在 data 文件夹（便携模式）
             如果存在：返回 EXE 所在目录
          2. 否则：返回用户 AppData 目录下的程序专用文件夹
             路径示例：C:/Users/xxx/AppData/Roaming/等保测评进度管理系统/

        源码运行模式（sys.frozen = False）：
          返回项目源码根目录（main.py 文件所在目录的上一级）

        Returns:
            str: 数据存储根目录的绝对路径
        """
        if getattr(sys, 'frozen', False):  # 检查是否在 PyInstaller 等打包环境中运行
            # 打包环境：先尝试便携模式
            exe_dir = os.path.dirname(sys.executable)  # 获取 EXE 文件所在目录
            portable_data = os.path.join(exe_dir, "data")  # 便携 data 文件夹路径
            if os.path.exists(portable_data):  # 如果便携 data 文件夹存在
                return exe_dir  # 使用便携模式（数据与 EXE 同目录）
            # 回退到用户 AppData 目录（EXE 更新不会影响此目录中的数据）
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))  # Windows AppData 或用户主目录
            base_dir = os.path.join(appdata, "等保测评进度管理系统")  # 程序专用目录
            return base_dir  # 返回 AppData 路径
        else:
            # 源码运行模式：返回项目根目录
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # utils/../ = 项目根目录
            return base_dir

    @classmethod
    def get_data_file_path(cls):
        """获取主数据文件完整路径

        Returns:
            str: data/dap_data.json 的完整绝对路径
        """
        return os.path.join(cls.get_data_dir(), "data", "dap_data.json")  # 拼接路径

    @classmethod
    def get_log_file_path(cls):
        """获取操作日志文件完整路径

        Returns:
            str: data/operation_log.json 的完整绝对路径
        """
        return os.path.join(cls.get_data_dir(), "data", "operation_log.json")  # 拼接路径

    # =========================================================================
    # 窗口几何信息持久化（原则 #5 技术隔离）
    # =========================================================================

    @classmethod
    def get_geometry_path(cls):
        """获取窗口几何信息文件路径。"""
        return os.path.join(cls.get_data_dir(), "data", "window_geometry.json")

    @classmethod
    def load_window_geometry(cls):
        """加载保存的窗口几何信息。

        Returns:
            str | None: 几何字符串，无保存文件时返回 None。
        """
        import json
        path = cls.get_geometry_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    return saved.get("geometry")
            except Exception as e:
                print(f"[Config] 窗口几何信息加载失败: {e}", flush=True)
        return None

    @classmethod
    def save_window_geometry(cls, geometry_str: str):
        """持久化窗口几何信息。

        Args:
            geometry_str: Tkinter 几何字符串（如 "1500x850+100+50"）。
        """
        import json
        path = cls.get_geometry_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"geometry": geometry_str}, f)
        except Exception as e:
            print(f"[Config] 窗口几何信息保存失败: {e}", flush=True)

    @classmethod
    def get_backup_dir(cls):
        """获取本地自动备份目录路径。"""
        return os.path.join(cls.get_data_dir(), "data", "backup")

    @classmethod
    def create_local_backup(cls, data_file_path: str):
        """创建本地自动备份，保留最近 30 个备份文件。

        Args:
            data_file_path: 主数据文件的完整路径。
        """
        import shutil
        from datetime import datetime
        backup_dir = cls.get_backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"dap_data_{ts}.json")
        if os.path.exists(data_file_path):
            shutil.copy2(data_file_path, backup_path)
            print(f"[备份] 已保存到 {backup_path}", flush=True)
        backups = sorted(os.listdir(backup_dir))
        while len(backups) > 30:
            os.remove(os.path.join(backup_dir, backups.pop(0)))

    # =============================================================================
    # 默认流程步骤 - 等保测评标准流程的 8 个阶段定义
    # =============================================================================

    @classmethod
    def get_default_workflow_stages(cls):
        """获取系统默认的流程阶段列表（每次调用生成新的唯一ID）。

        等保测评标准流程的 8 个阶段，ID 通过 generate_id() 动态生成，
        避免硬编码固定 ID 与用户自定义阶段 ID 不一致的问题（原则 #3）。

        Returns:
            list[dict]: 包含 8 个默认阶段的字典列表。
        """
        from utils.helpers import generate_id
        return [
            {"id": generate_id("stage"), "name": "项目启动", "order": 0, "color": "#3498db"},
            {"id": generate_id("stage"), "name": "现状调研", "order": 1, "color": "#2ecc71"},
            {"id": generate_id("stage"), "name": "差距评估", "order": 2, "color": "#e67e22"},
            {"id": generate_id("stage"), "name": "方案设计", "order": 3, "color": "#9b59b6"},
            {"id": generate_id("stage"), "name": "整改实施", "order": 4, "color": "#e74c3c"},
            {"id": generate_id("stage"), "name": "测评验收", "order": 5, "color": "#1abc9c"},
            {"id": generate_id("stage"), "name": "报告输出", "order": 6, "color": "#f39c12"},
            {"id": generate_id("stage"), "name": "项目归档", "order": 7, "color": "#95a5a6"},
        ]

    # =============================================================================
    # UI 样式配置 - 看板界面的视觉参数
    # =============================================================================

    # --- 看板颜色体系 ---
    KANBAN_BG = "#f0f2f5"     # 看板整体背景色（浅灰蓝，柔和视觉）
    COLUMN_BG = "#e8eaed"     # 单列背景色（浅灰，与看板区分层次）
    COLUMN_HEADER_BG = "#dfe1e6"  # 列标题背景色（略深灰，形成视觉层次）
    CARD_BG = "#ffffff"       # 卡片背景色（纯白，模拟纸质卡片的物理感）
    CARD_BORDER = "#d0d5dd"   # 卡片边框颜色（浅灰，柔和边界）
    CARD_HOVER_BG = "#f8f9fa" # 鼠标悬停时卡片背景色（极浅灰，微妙反馈）

    # --- 字体配置 ---
    FONT_FAMILY = "Microsoft YaHei"  # 默认字体族（微软雅黑，Windows 最佳中文显示效果）
    FONT_SIZE_SMALL = 9               # 小字号 - 辅助信息、提示文字
    FONT_SIZE_NORMAL = 10             # 正常字号 - 正文内容、按钮文字
    FONT_SIZE_LARGE = 12              # 大字号 - 子标题
    FONT_SIZE_TITLE = 14              # 标题字号 - 区块标题
    FONT_SIZE_HEADER = 16             # 页头字号 - 窗口/对话框标题

    # --- 窗口默认尺寸 ---
    WINDOW_WIDTH = 1500  # 主窗口默认宽度（像素），适配 1920x1080 屏幕
    WINDOW_HEIGHT = 850  # 主窗口默认高度（像素），留出任务栏和状态栏空间
    WINDOW_MIN_WIDTH = 900   # 主窗口最小宽度（防止缩得过小导致布局错乱）
    WINDOW_MIN_HEIGHT = 500  # 主窗口最小高度

    # --- 卡片尺寸 ---
    CARD_WIDTH = 200       # 每张项目卡片的固定宽度（像素）
    CARD_MIN_HEIGHT = 80   # 每张项目卡片的最小高度（像素）

    # --- 列尺寸 ---
    COLUMN_WIDTH = 260        # 每个阶段列的默认宽度（像素）
    COLUMN_MIN_HEIGHT = 400   # 每个阶段列的最小高度（像素）

    # --- 工具栏尺寸 ---
    TOOLBAR_HEIGHT = 45  # 顶部工具栏固定高度（像素），足够容纳按钮和提示

    # =============================================================================
    # 日期格式 - 统一的日期时间显示格式
    # =============================================================================

    DATE_FORMAT = "%Y-%m-%d"              # 日期显示格式：YYYY-MM-DD（如 2026-06-03）
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S" # 日期时间显示格式：YYYY-MM-DD HH:MM:SS

    # =============================================================================
    # 状态颜色映射 - 不同项目状态对应的卡片背景色
    # =============================================================================

    STATUS_COLORS = {
        "completed": "#92d050",   # 绿色：已完成 / 已结项（最后阶段）
        "normal":    "#00b0f0",   # 蓝色：进行中
        "warning":   "#ffc000",   # 黄色：延期风险 / 需关注（≤7 天到期）
        "overdue":   "#ff0000",   # 红色：严重延误（已超期）
        "inactive":  "#d9d9d9",   # 灰色：无截止日期
    }

    # =============================================================================
    # 业务配置
    # =============================================================================

    DEADLINE_WARNING_DAYS = 7  # 截止日期前多少天开始显示橙色预警（0 天不预警，7 天提前提醒）
