"""
Data Transfer Objects (DTOs) 模块 — 为层间数据交换提供类型安全的数据结构。

本模块使用 Python dataclasses 定义类型化的数据传输对象，用于：
- 从 UI 层向服务层传递项目创建/更新数据（ProjectCreateDTO / ProjectUpdateDTO）
- 封装对话框返回的结果数据（ProjectResultDTO）
- 表示流程阶段的配置数据（WorkflowStageDTO）

所有 DTO 均使用 from __future__ import annotations 实现延迟注解求值，
并通过显式类型提示让接口契约清晰可读。
"""

# ---------------------------------------------------------------------------
# 延迟注解求值：使所有类型提示在所有 Python 版本中表现为字符串形式，
# 避免循环导入问题并允许前向引用。
# ---------------------------------------------------------------------------
from __future__ import annotations

# ---------------------------------------------------------------------------
# 标准库导入
# ---------------------------------------------------------------------------
from dataclasses import dataclass, field
# dataclass: 自动生成 __init__、__repr__、__eq__ 等魔术方法
# field: 为 dataclass 字段指定默认工厂函数等元数据

from typing import Optional
# Optional[X] 等价于 X | None，用于标记可选字段


# ===========================================================================
# ProjectCreateDTO — 创建项目时所需的数据
# ===========================================================================

@dataclass
class ProjectCreateDTO:
    """用于创建新项目的 DTO。

    包含创建等保测评项目所需的全部业务字段。
    每个字段均有默认值，支持从 UI 表单逐步填充或从字典反序列化。

    属性说明:
        company_name (str): 被测评单位的公司名称。
        system_name (str): 被测信息系统名称。
        cert_number (str): 备案证书编号。
        issue_date (str): 证书颁发日期（YYYY-MM-DD 格式）。
        level (str): 系统保护等级（如：第二级、第三级）。
        location (str): 项目所在地/机房位置。
        deadline (str): 项目截止日期。
        notes (str): 备注信息（自由文本）。
        stage_id (str): 初始流程阶段 ID，关联 WorkflowStage.id。
        folder_path (str): 项目相关文件的本地存储路径。
    """

    company_name: str = ""      # 被测评单位的公司名称
    system_name: str = ""       # 被测信息系统名称
    cert_number: str = ""       # 备案证书编号
    issue_date: str = ""        # 证书颁发日期（YYYY-MM-DD 格式）
    level: str = ""             # 系统保护等级（如：第二级、第三级）
    location: str = ""          # 项目所在地/机房位置
    deadline: str = ""          # 项目截止日期
    notes: str = ""             # 备注信息（自由文本）
    stage_id: str = ""          # 初始流程阶段 ID，关联 WorkflowStage.id
    folder_path: str = ""       # 项目相关文件的本地存储路径


# ===========================================================================
# ProjectUpdateDTO — 部分更新项目时所需的数据
# ===========================================================================

@dataclass
class ProjectUpdateDTO:
    """用于部分更新现有项目的 DTO。

    所有字段均为 Optional（默认为 None），表示"未传入则不更新"。
    与 Project.update() 方法的参数签名保持一致。

    属性说明:
        company_name (Optional[str]): 新的公司名称，None 表示保持不变。
        system_name (Optional[str]): 新的系统名称，None 表示保持不变。
        cert_number (Optional[str]): 新的证书编号，None 表示保持不变。
        issue_date (Optional[str]): 新的颁发日期，None 表示保持不变。
        level (Optional[str]): 新的保护等级，None 表示保持不变。
        location (Optional[str]): 新的所在地，None 表示保持不变。
        deadline (Optional[str]): 新的截止日期，None 表示保持不变。
        notes (Optional[str]): 新的备注，None 表示保持不变。
        stage_id (Optional[str]): 新的阶段ID，None 表示保持不变。
        folder_path (Optional[str]): 新的文件夹路径，None 表示保持不变。
    """

    company_name: Optional[str] = None   # 新的公司名称（None 表示不更新）
    system_name: Optional[str] = None    # 新的系统名称（None 表示不更新）
    cert_number: Optional[str] = None    # 新的证书编号（None 表示不更新）
    issue_date: Optional[str] = None     # 新的颁发日期（None 表示不更新）
    level: Optional[str] = None          # 新的保护等级（None 表示不更新）
    location: Optional[str] = None       # 新的所在地（None 表示不更新）
    deadline: Optional[str] = None       # 新的截止日期（None 表示不更新）
    notes: Optional[str] = None          # 新的备注（None 表示不更新）
    stage_id: Optional[str] = None       # 新的阶段ID（None 表示不更新）
    folder_path: Optional[str] = None    # 新的文件夹路径（None 表示不更新）


# ===========================================================================
# ProjectResultDTO — 对话框返回的项目数据结果
# ===========================================================================

@dataclass
class ProjectResultDTO:
    """项目编辑对话框返回的结果 DTO。

    封装 show_project_dialog() 返回值的数据结构，
    与 ProjectDialog._on_confirm() 中构建的 self.result 字典格式一致。

    systems 字段用于支持一个项目下包含多个被测系统的场景。

    属性说明:
        company_name (str): 公司名称。
        system_name (str): 系统名称。
        cert_number (str): 证书编号。
        issue_date (str): 下证日期。
        level (str): 系统保护等级。
        location (str): 属地（省-市格式）。
        deadline (str): 交付日期。
        notes (str): 备注内容。
        stage_id (str): 流程阶段 ID。
        folder_path (str): 项目文件夹路径。
        systems (list): 关联的系统列表，用于多系统项目场景。
    """

    company_name: str = ""      # 公司名称
    system_name: str = ""       # 系统名称
    cert_number: str = ""       # 证书编号
    issue_date: str = ""        # 下证日期
    level: str = ""             # 系统保护等级
    location: str = ""          # 属地（省-市格式）
    deadline: str = ""          # 交付日期
    notes: str = ""             # 备注内容
    stage_id: str = ""          # 流程阶段 ID
    folder_path: str = ""       # 项目文件夹路径
    systems: list = field(default_factory=list)  # 关联的系统列表（多系统项目场景）


# ===========================================================================
# WorkflowStageDTO — 流程阶段配置数据
# ===========================================================================

@dataclass
class WorkflowStageDTO:
    """流程阶段配置的 DTO。

    表示看板中一个流程列的完整配置信息，用于在服务层与 UI 层之间
    传递阶段数据。与 WorkflowStage 实体类保持字段对应。

    属性说明:
        name (str): 阶段显示名称（如：项目启动、现状调研、安全测评）。
        order (int): 排序序号，决定在看板中的左右位置。
        color (str): 阶段标识颜色，十六进制颜色码（如 "#3498db"）。
        column_width (Optional[int]): 看板列宽度（像素），None 表示系统默认。
        stage_id (str): 阶段唯一标识符，已有阶段传入以保持 ID 不变。
    """

    name: str = ""                  # 阶段显示名称（如：项目启动、现状调研、安全测评）
    order: int = 0                  # 排序序号，决定在看板中的左右位置
    color: str = "#3498db"          # 阶段标识颜色，十六进制颜色码
    column_width: Optional[int] = None  # 看板列宽度（像素），None 表示系统默认
    stage_id: str = ""              # 阶段唯一标识符（已有阶段传入以保持 ID 不变）
