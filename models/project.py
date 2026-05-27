"""
项目实体类 - 表示一个等保测评项目

每个项目包含公司名称、系统名称、当前进度阶段、时间信息和备注
"""

from datetime import datetime  # 日期时间模块（虽然未直接使用，但保留以备用）
from utils.helpers import generate_id, get_now_str  # 导入ID生成函数和当前时间获取函数


class Project:
    """等保测评项目实体

    Attributes:
        id: 项目唯一标识（基于时间戳自动生成，格式如 proj_1234567890123）
        company_name: 被测评单位名称
        system_name: 被测评信息系统名称
        filing_number: 系统备案号（公安机关备案编号）
        deadline: 项目截止日期（YYYY-MM-DD格式）
        notes: 备注信息（多行文本，用于记录额外事项）
        stage_id: 当前所处流程阶段的ID（对应 WorkflowStage 的 id）
        created_at: 项目创建时间（YYYY-MM-DD HH:MM:SS格式）
        updated_at: 项目最后更新时间（YYYY-MM-DD HH:MM:SS格式）
    """

    def __init__(self, company_name: str = "", system_name: str = "",
                 filing_number: str = "", deadline: str = "",
                 notes: str = "", stage_id: str = "",
                 project_id: str = "", created_at: str = "",
                 updated_at: str = ""):
        """初始化项目对象
        支持从现有数据重建（提供project_id时）或新建项目（不提供时自动生成）
        """
        self.id = project_id or generate_id("proj")  # 使用传入的ID或自动生成以 "proj" 为前缀的新ID
        self.company_name = company_name  # 公司名称
        self.system_name = system_name    # 系统名称
        self.filing_number = filing_number  # 备案号
        self.deadline = deadline  # 截止日期
        self.notes = notes  # 备注信息
        self.stage_id = stage_id  # 当前阶段ID
        self.created_at = created_at or get_now_str()  # 创建时间（为空则取当前时间）
        self.updated_at = updated_at or get_now_str()  # 更新时间（为空则取当前时间）

    @property
    def name(self) -> str:
        """组合显示名称：公司名称 + 系统名称
        将公司名和系统名用短横线连接，便于在卡片和列表中展示项目身份
        """
        if self.company_name and self.system_name:  # 两者都有时
            return f"{self.company_name}-{self.system_name}"  # 用短横线连接显示
        return self.company_name or self.system_name or ""  # 只有一个时返回有值的那个，都没有返回空串

    def to_dict(self) -> dict:
        """将项目对象序列化为字典，便于JSON存储"""
        return {
            "id": self.id,                       # 项目ID
            "company_name": self.company_name,   # 公司名称
            "system_name": self.system_name,     # 系统名称
            "filing_number": self.filing_number, # 备案号
            "deadline": self.deadline,           # 截止日期
            "notes": self.notes,                 # 备注
            "stage_id": self.stage_id,           # 当前阶段ID
            "created_at": self.created_at,       # 创建时间
            "updated_at": self.updated_at,       # 更新时间
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """从字典反序列化创建项目对象
        兼容旧数据格式：如果旧数据只有 name 字段而没有 company_name/system_name，
        则尝试从 name 字段中按分隔符拆分出公司名和系统名
        """
        # 兼容旧数据：若缺少新字段则从 name 字段迁移
        company = data.get("company_name", "")  # 尝试获取公司名称
        system = data.get("system_name", "")    # 尝试获取系统名称
        if not company and not system:  # 如果两个新字段都为空，说明可能是旧格式数据
            old_name = data.get("name", "")  # 读取旧数据的 name 字段
            if old_name:  # name字段有内容
                # 尝试按常见分隔符拆分旧名称
                for sep in ("-", "—", "—", "/"):  # 遍历常见的分隔符
                    parts = old_name.split(sep, 1)  # 按分隔符拆分成两部分
                    if len(parts) == 2 and parts[0].strip() and parts[1].strip():  # 拆分成功且两部分都非空
                        company = parts[0].strip()  # 第一部分作为公司名
                        system = parts[1].strip()   # 第二部分作为系统名
                        break  # 找到合适的分隔符后退出循环
                if not company:  # 所有分隔符都不匹配，整个name作为公司名
                    company = old_name.strip()

        return cls(  # 使用解析后的数据创建Project实例
            company_name=company,
            system_name=system,
            filing_number=data.get("filing_number", ""),  # 提取备案号，不存在则为空
            deadline=data.get("deadline", ""),  # 提取截止日期
            notes=data.get("notes", ""),  # 提取备注
            stage_id=data.get("stage_id", ""),  # 提取阶段ID
            project_id=data.get("id", ""),  # 使用现有ID
            created_at=data.get("created_at", ""),  # 提取创建时间
            updated_at=data.get("updated_at", ""),  # 提取更新时间
        )

    def update(self, company_name: str = None, system_name: str = None,
               filing_number: str = None,
               deadline: str = None, notes: str = None, stage_id: str = None):
        """更新项目属性，只更新传入的非None字段
        使用None作为默认值可区分"不更新"和"更新为空"两种情况
        """
        if company_name is not None:  # 传入公司名称参数则更新
            self.company_name = company_name
        if system_name is not None:  # 传入系统名称参数则更新
            self.system_name = system_name
        if filing_number is not None:  # 传入备案号参数则更新
            self.filing_number = filing_number
        if deadline is not None:  # 传入截止日期参数则更新
            self.deadline = deadline
        if notes is not None:  # 传入备注参数则更新
            self.notes = notes
        if stage_id is not None:  # 传入阶段ID参数则更新
            self.stage_id = stage_id
        self.updated_at = get_now_str()  # 不管更新了哪些字段，都刷新更新时间戳

    def __repr__(self) -> str:
        """对象的字符串表示，用于调试输出"""
        return f"Project(id={self.id}, name={self.name}, stage={self.stage_id})"
