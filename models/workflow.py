"""
流程阶段实体模块 - 定义等保测评流程中每个阶段的属性。

本模块提供 WorkflowStage 类，代表看板上的一个流程列（如"项目启动"、
"现状调研"、"安全测评"等），支持以下特性：
- 阶段的唯一标识和显示名称
- 看板列排序（通过 order 字段控制左右位置）
- 列颜色标识（十六进制颜色码）
- 列宽自定义（像素值，支持用户拖拽调整）

同时提供字典序列化/反序列化能力，用于 JSON 持久化存储和前端渲染。
"""

# ---------------------------------------------------------------------------
# 项目内导入（自建工具库）
# ---------------------------------------------------------------------------
from utils.helpers import generate_id
# generate_id: 生成带有指定前缀的唯一标识符，用于为新阶段分配全局唯一ID


class WorkflowStage:
    """流程阶段实体类。

    每个 WorkflowStage 实例代表等保测评看板中的一个流程列。
    阶段决定项目在看板上的位置（哪个列），所有阶段按 order 从左到右排列。

    属性说明:
        id (str): 阶段唯一标识符，格式为 "stage_" 前缀加时间戳哈希。
        name (str): 阶段显示名称（如：项目启动、现状调研、安全测评等）。
        order (int): 排序序号，从 0 开始递增，决定在看板中的左右位置。
        color (str): 阶段标识颜色，十六进制颜色码（如 "#3498db"）。
        column_width (int | None): 看板列宽度（像素），None 表示使用系统默认列宽。
    """

    def __init__(self, name: str = "", order: int = 0,
                 color: str = "#3498db", stage_id: str = "",
                 column_width: int = None):
        """初始化流程阶段对象。

        Args:
            name: 阶段显示名称，直接展示在看板列标题上。
            order: 排序序号，数值越小越靠左，从 0 开始。
            color: 标识颜色，用于列标题背景等位置的十六进制颜色码。
            stage_id: 已有阶段ID（反序列化时传入），为空则自动生成以 "stage" 为前缀的新ID。
            column_width: 列宽度（像素），None 表示使用系统默认值。
        """
        # 阶段ID：优先使用传入的已有ID，否则自动生成以 "stage" 为前缀的唯一ID
        self.id = stage_id or generate_id("stage")

        # ---- 阶段核心属性 ----
        self.name = name               # 阶段显示名称
        self.order = order             # 排序序号（决定看板列位置）
        self.color = color             # 标识颜色（十六进制颜色码）
        self.column_width = column_width  # 列宽（None = 系统默认值）

    # ========================================================================
    # 序列化 / 反序列化
    # ========================================================================

    def to_dict(self) -> dict:
        """将阶段对象序列化为字典，用于 JSON 持久化存储。

        将所有属性导出为纯字典格式，便于 json.dump() 写入数据文件。
        注意: column_width 为 None 时在 JSON 中表示为 null，表示使用默认值。

        Returns:
            dict: 包含阶段所有属性的字典。
        """
        return {
            "id": self.id,                     # 阶段唯一标识
            "name": self.name,                 # 阶段显示名称
            "order": self.order,               # 排序序号
            "color": self.color,               # 标识颜色
            "column_width": self.column_width,  # 列宽（可为 None）
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowStage":
        """从字典反序列化创建流程阶段对象。

        Args:
            data: 包含阶段属性的字典，通常从 JSON 数据文件解析而来。

        Returns:
            WorkflowStage: 反序列化后的阶段对象，缺失字段使用默认值。
        """
        return cls(
            name=data.get("name", ""),                  # 提取名称，默认空字符串
            order=data.get("order", 0),                 # 提取序号，默认 0
            color=data.get("color", "#3498db"),          # 提取颜色，默认蓝色
            stage_id=data.get("id", ""),                 # 提取已有ID，保持标识不变
            column_width=data.get("column_width"),       # 提取列宽，None 表示默认
        )

    # ========================================================================
    # 调试输出
    # ========================================================================

    def __repr__(self) -> str:
        """对象的调试字符串表示，便于开发调试时快速识别阶段。

        Returns:
            str: 包含阶段ID、名称和排序号的简要描述。
        """
        return f"WorkflowStage(id={self.id}, name={self.name}, order={self.order})"
