"""
流程阶段实体类 - 表示等保测评流程中的一个阶段

每个阶段有名称、排序和颜色标识，可以动态增删改
"""

from utils.helpers import generate_id  # 导入ID生成函数，用于为新阶段生成唯一标识


class WorkflowStage:
    """流程阶段实体
    代表等保测评看板中的一个流程列，如"项目启动"、"现状调研"等

    Attributes:
        id: 阶段唯一标识（自动生成，格式如 stage_1234567890123）
        name: 阶段名称（如：项目启动、现状调研等）
        order: 排序序号（从0开始，决定在看板中的左右位置）
        color: 阶段标识颜色（十六进制颜色码，如 #3498db）
    """

    def __init__(self, name: str = "", order: int = 0,
                 color: str = "#3498db", stage_id: str = "",
                 column_width: int = None):
        """初始化流程阶段对象

        Args:
            name: 阶段显示名称
            order: 排序序号，决定阶段在看板中的位置
            color: 标识颜色，十六进制颜色码
            stage_id: 阶段ID（为空时自动生成以 "stage" 为前缀的新ID）
            column_width: 看板列宽（像素），None表示使用系统默认值
        """
        self.id = stage_id or generate_id("stage")  # 使用传入ID或自动生成新ID
        self.name = name    # 阶段名称
        self.order = order  # 排序序号
        self.color = color  # 标识颜色
        self.column_width = column_width  # 列宽（None=系统默认）

    def to_dict(self) -> dict:
        """将阶段对象序列化为字典，便于JSON存储"""
        return {
            "id": self.id,       # 阶段ID
            "name": self.name,   # 阶段名称
            "order": self.order, # 排序序号
            "color": self.color, # 标识颜色
            "column_width": self.column_width,  # 列宽
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowStage":
        """从字典反序列化创建阶段对象

        Args:
            data: 包含阶段属性的字典（通常来自JSON数据）

        Returns:
            反序列化后的WorkflowStage对象
        """
        return cls(
            name=data.get("name", ""),                     # 提取名称，默认为空
            order=data.get("order", 0),                    # 提取序号，默认为0
            color=data.get("color", "#3498db"),            # 提取颜色，默认为蓝色
            stage_id=data.get("id", ""),                   # 提取ID，使用现有ID
            column_width=data.get("column_width"),          # 提取列宽（None=默认）
        )

    def __repr__(self) -> str:
        """对象的字符串表示，用于调试输出"""
        return f"WorkflowStage(id={self.id}, name={self.name}, order={self.order})"
