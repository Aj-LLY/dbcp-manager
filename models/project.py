"""
项目实体模块 - 定义等保测评项目的核心数据模型。

本模块提供 Project 类，封装单个等保测评项目的全部属性，包括：
- 项目基本信息（公司名称、系统名称、证书编号、等级等）
- 时间信息（创建时间、更新时间、截止日期）
- 流程状态（当前所处阶段ID）
- 文件路径（项目文件夹路径）

同时提供字典序列化/反序列化能力，用于 JSON 持久化存储。
历史数据兼容：支持从旧版 "name" 字段自动拆分为 company_name 和 system_name。
"""

# ---------------------------------------------------------------------------
# 延迟注解求值
# ---------------------------------------------------------------------------
from __future__ import annotations

# ---------------------------------------------------------------------------
# 项目内导入（自建工具库）
# ---------------------------------------------------------------------------
from utils.helpers import generate_id, get_now_str
# generate_id: 生成带有指定前缀的唯一标识符，如 "proj_xxxxxxxxxxxx"
# get_now_str: 获取当前时间的格式化字符串（YYYY-MM-DD HH:MM:SS）


class Project:
    """等保测评项目实体类。

    每个 Project 实例代表一个等保测评项目，包含项目的完整信息。
    name 属性为只读计算属性，由 company_name 和 system_name 拼接而成。

    属性说明:
        id (str): 项目唯一标识符，格式为 "proj_" 前缀加时间戳哈希，全局唯一。
        company_name (str): 被测评单位的公司名称。
        system_name (str): 被测评的信息系统名称。
        cert_number (str): 备案证书编号。
        issue_date (str): 证书颁发日期。
        level (str): 系统保护等级（如：第二级、第三级）。
        location (str): 项目所在地/机房位置。
        folder_path (str): 项目相关文件的本地存储路径。
        deadline (str): 项目截止日期。
        notes (str): 备注信息（自由文本）。
        stage_id (str): 项目当前所处的流程阶段ID，关联 WorkflowStage.id。
        created_at (str): 项目创建时间（系统自动设置）。
        updated_at (str): 项目最后更新时间（系统自动维护）。
        name (str, 只读属性): 项目显示名称，格式为 "公司名称-系统名称"。
    """

    def __init__(self, company_name: str = "", system_name: str = "",
                 cert_number: str = "", issue_date: str = "",
                 level: str = "", location: str = "",
                 deadline: str = "", notes: str = "", stage_id: str = "",
                 project_id: str = "", created_at: str = "",
                 updated_at: str = "", folder_path: str = ""):
        """初始化项目对象。

        所有参数均有默认值，允许创建空项目或从字典反序列化时部分填充。

        Args:
            company_name: 被测评单位公司名称。
            system_name: 被测评信息系统名称。
            cert_number: 备案证书编号。
            issue_date: 证书颁发日期。
            level: 系统保护等级。
            location: 项目所在地。
            deadline: 项目截止日期。
            notes: 备注信息。
            stage_id: 当前所处流程阶段ID。
            project_id: 已有项目ID（反序列化时传入），为空则自动生成。
            created_at: 创建时间字符串，为空则使用当前时间。
            updated_at: 更新时间字符串，为空则使用当前时间。
            folder_path: 项目文件夹路径。
        """
        # 项目ID：优先使用传入的已有ID，否则自动生成以 "proj" 为前缀的唯一ID
        self.id = project_id or generate_id("proj")

        # ---- 项目基本信息 ----
        self.company_name = company_name   # 被测评单位名称
        self.system_name = system_name     # 被测信息系统名称
        self.cert_number = cert_number     # 备案证书编号
        self.issue_date = issue_date       # 证书颁发日期
        self.level = level                 # 系统保护等级
        self.location = location           # 项目所在地/机房位置
        self.folder_path = folder_path     # 项目文件存储路径
        self.deadline = deadline           # 项目截止日期
        self.notes = notes                 # 项目备注信息
        self.stage_id = stage_id           # 当前流程阶段ID

        # ---- 时间戳（自动时间） ----
        # 创建时间：反序列化时使用已有值，新建时自动设为当前时间
        self.created_at = created_at or get_now_str()
        # 更新时间：反序列化时使用已有值，新建时自动设为当前时间
        self.updated_at = updated_at or get_now_str()

    # ========================================================================
    # 只读计算属性
    # ========================================================================

    @property
    def name(self) -> str:
        """项目显示名称（只读计算属性）。

        自动将公司名称和系统名称拼接为可读的项目名。
        命名规则：
        - 两者都有: "公司名称-系统名称"
        - 只有其一时: 返回有值的那个
        - 都为空时: 返回空字符串

        Returns:
            str: 拼接后的项目显示名称。
        """
        if self.company_name and self.system_name:
            # 公司和系统名都有，用短横线连接
            return f"{self.company_name}-{self.system_name}"
        # 只有其中之一或都为空，返回有值的那个（或空串）
        return self.company_name or self.system_name or ""

    # ========================================================================
    # 序列化 / 反序列化
    # ========================================================================

    def to_dict(self) -> dict:
        """将项目对象序列化为字典，用于 JSON 持久化存储。

        所有属性值被导出为纯字典，便于 json.dump() 写入文件。

        Returns:
            dict: 包含项目所有属性的字典，键名为 JSON 字段名。
        """
        return {
            "id": self.id,                     # 项目唯一标识
            "company_name": self.company_name,  # 公司名称
            "system_name": self.system_name,    # 系统名称
            "cert_number": self.cert_number,    # 证书编号
            "issue_date": self.issue_date,      # 颁发日期
            "level": self.level,                # 保护等级
            "location": self.location,          # 项目所在地
            "folder_path": self.folder_path,    # 文件夹路径
            "deadline": self.deadline,          # 截止日期
            "notes": self.notes,                # 备注
            "stage_id": self.stage_id,          # 当前阶段ID
            "created_at": self.created_at,      # 创建时间
            "updated_at": self.updated_at,      # 更新时间
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """从字典反序列化创建项目对象。

        支持两种数据格式：
        1. 新版格式：直接包含 company_name 和 system_name 字段。
        2. 旧版格式（历史兼容）：只有 name 字段，自动尝试按分隔符
           （"-", "/", "/"）拆分为 company_name 和 system_name。

        Args:
            data: 项目数据字典，通常从 JSON 文件解析而来。

        Returns:
            Project: 反序列化后的项目对象。
        """
        company = data.get("company_name", "")   # 尝试获取新版公司名
        system = data.get("system_name", "")     # 尝试获取新版系统名

        # 历史数据兼容：如果新版字段不存在，尝试从旧版 name 字段拆分
        if not company and not system:
            old_name = data.get("name", "")      # 获取旧版单一名称字段
            if old_name:
                # 按常见分隔符依次尝试拆分
                for sep in ("-", "/", "/"):
                    parts = old_name.split(sep, 1)       # 只分割一次（最多产生两部分）
                    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                        # 拆分成功且两部分都非空
                        company = parts[0].strip()
                        system = parts[1].strip()
                        break
                if not company:
                    # 所有分隔符都未匹配，将整个名称作为公司名
                    company = old_name.strip()

        # 使用提取/解析出的字段构建 Project 实例
        return cls(
            company_name=company,
            system_name=system,
            cert_number=data.get("cert_number") or data.get("filing_number", ""),
            # 证书编号兼容旧字段名 filing_number
            issue_date=data.get("issue_date", ""),
            level=data.get("level", ""),
            location=data.get("location", ""),
            folder_path=data.get("folder_path", ""),
            deadline=data.get("deadline", ""),
            notes=data.get("notes", ""),
            stage_id=data.get("stage_id", ""),
            project_id=data.get("id", ""),       # 使用已有ID，避免重新生成
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    # ========================================================================
    # 数据更新
    # ========================================================================

    def update(self, company_name=None, system_name=None, cert_number=None,
               issue_date=None, level=None, location=None,
               deadline=None, notes=None, stage_id=None, folder_path=None) -> None:
        """部分更新项目属性（只更新传入的非 None 字段）。

        采用 "仅更新传入字段" 的策略，未传入的字段保持原值不变。
        更新后自动刷新 updated_at 时间戳。

        Args:
            company_name: 新的公司名称（None 表示不更新）。
            system_name: 新的系统名称（None 表示不更新）。
            cert_number: 新的证书编号（None 表示不更新）。
            issue_date: 新的颁发日期（None 表示不更新）。
            level: 新的保护等级（None 表示不更新）。
            location: 新的所在地（None 表示不更新）。
            deadline: 新的截止日期（None 表示不更新）。
            notes: 新的备注（None 表示不更新）。
            stage_id: 新的阶段ID（None 表示不更新）。
            folder_path: 新的文件夹路径（None 表示不更新）。
        """
        # 每个字段独立判断：只有传入非 None 值才更新
        if company_name is not None:
            self.company_name = company_name
        if system_name is not None:
            self.system_name = system_name
        if cert_number is not None:
            self.cert_number = cert_number
        if issue_date is not None:
            self.issue_date = issue_date
        if level is not None:
            self.level = level
        if location is not None:
            self.location = location
        if deadline is not None:
            self.deadline = deadline
        if notes is not None:
            self.notes = notes
        if stage_id is not None:
            self.stage_id = stage_id
        if folder_path is not None:
            self.folder_path = folder_path

        # 任何字段更新后，自动刷新最后更新时间戳
        self.updated_at = get_now_str()

    # ========================================================================
    # 调试输出
    # ========================================================================

    def __repr__(self) -> str:
        """对象的调试字符串表示，便于开发和日志输出。

        Returns:
            str: 包含项目ID和名称的简要描述。
        """
        return f"Project(id={self.id}, name={self.name})"
