"""
项目实体类 - 表示一个等保测评项目

每个项目包含公司名称、系统名称、当前进度阶段、时间信息和备注
"""

from datetime import datetime  # 日期时间模块
from utils.helpers import generate_id, get_now_str  # ID生成和当前时间获取


class Project:
    """等保测评项目实体

    Attributes:
        id: 项目唯一标识（基于时间戳自动生成）
        company_name: 被测评单位名称
        system_name: 被测评信息系统名称
        cert_number: 系统备案号（公安机关备案编号）
        issue_date: 下证日期（YYYY-MM-DD格式）
        level: 系统等级（如"第二级"）
        deadline: 项目预计交付日期（YYYY-MM-DD格式）
        notes: 备注信息（多行文本）
        stage_id: 当前所处流程阶段的ID
        created_at: 项目创建时间
        updated_at: 项目最后更新时间
    """

    def __init__(self, company_name: str = "", system_name: str = "",
                 cert_number: str = "", issue_date: str = "",
                 level: str = "", deadline: str = "",
                 notes: str = "", stage_id: str = "",
                 project_id: str = "", created_at: str = "",
                 updated_at: str = ""):
        """初始化项目对象"""
        self.id = project_id or generate_id("proj")
        self.company_name = company_name
        self.system_name = system_name
        self.cert_number = cert_number
        self.issue_date = issue_date  # 下证日期
        self.level = level            # 系统等级
        self.deadline = deadline      # 项目预计交付日期
        self.notes = notes
        self.stage_id = stage_id
        self.created_at = created_at or get_now_str()
        self.updated_at = updated_at or get_now_str()

    @property
    def name(self) -> str:
        """组合显示名称：公司名称 + 系统名称"""
        if self.company_name and self.system_name:
            return f"{self.company_name}-{self.system_name}"
        return self.company_name or self.system_name or ""

    def to_dict(self) -> dict:
        """将项目对象序列化为字典"""
        return {
            "id": self.id,
            "company_name": self.company_name,
            "system_name": self.system_name,
            "cert_number": self.cert_number,
            "issue_date": self.issue_date,
            "level": self.level,
            "deadline": self.deadline,
            "notes": self.notes,
            "stage_id": self.stage_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """从字典反序列化创建项目对象（兼容旧数据格式）"""
        company = data.get("company_name", "")
        system = data.get("system_name", "")
        if not company and not system:
            old_name = data.get("name", "")
            if old_name:
                for sep in ("-", "—", "—", "/"):
                    parts = old_name.split(sep, 1)
                    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                        company = parts[0].strip()
                        system = parts[1].strip()
                        break
                if not company:
                    company = old_name.strip()

        return cls(
            company_name=company,
            system_name=system,
            cert_number=data.get("cert_number") or data.get("filing_number", ""),
            issue_date=data.get("issue_date", ""),
            level=data.get("level", ""),
            deadline=data.get("deadline", ""),
            notes=data.get("notes", ""),
            stage_id=data.get("stage_id", ""),
            project_id=data.get("id", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def update(self, company_name: str = None, system_name: str = None,
               cert_number: str = None, issue_date: str = None,
               level: str = None, deadline: str = None,
               notes: str = None, stage_id: str = None):
        """更新项目属性，只更新传入的非None字段"""
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
        if deadline is not None:
            self.deadline = deadline
        if notes is not None:
            self.notes = notes
        if stage_id is not None:
            self.stage_id = stage_id
        self.updated_at = get_now_str()

    def __repr__(self) -> str:
        return f"Project(id={self.id}, name={self.name}, stage={self.stage_id})"
