"""
项目实体类 - 表示一个等保测评项目
"""

from utils.helpers import generate_id, get_now_str


class Project:
    """等保测评项目实体"""

    def __init__(self, company_name: str = "", system_name: str = "",
                 cert_number: str = "", issue_date: str = "",
                 level: str = "", location: str = "",
                 deadline: str = "", notes: str = "", stage_id: str = "",
                 project_id: str = "", created_at: str = "",
                 updated_at: str = ""):
        self.id = project_id or generate_id("proj")
        self.company_name = company_name
        self.system_name = system_name
        self.cert_number = cert_number
        self.issue_date = issue_date
        self.level = level
        self.location = location  # 属地（省区-市区）
        self.deadline = deadline
        self.notes = notes
        self.stage_id = stage_id
        self.created_at = created_at or get_now_str()
        self.updated_at = updated_at or get_now_str()

    @property
    def name(self) -> str:
        if self.company_name and self.system_name:
            return f"{self.company_name}-{self.system_name}"
        return self.company_name or self.system_name or ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_name": self.company_name,
            "system_name": self.system_name,
            "cert_number": self.cert_number,
            "issue_date": self.issue_date,
            "level": self.level,
            "location": self.location,
            "deadline": self.deadline,
            "notes": self.notes,
            "stage_id": self.stage_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        company = data.get("company_name", "")
        system = data.get("system_name", "")
        if not company and not system:
            old_name = data.get("name", "")
            if old_name:
                for sep in ("-", "—", "/"):
                    parts = old_name.split(sep, 1)
                    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                        company = parts[0].strip()
                        system = parts[1].strip()
                        break
                if not company:
                    company = old_name.strip()
        return cls(
            company_name=company, system_name=system,
            cert_number=data.get("cert_number") or data.get("filing_number", ""),
            issue_date=data.get("issue_date", ""),
            level=data.get("level", ""),
            location=data.get("location", ""),
            deadline=data.get("deadline", ""),
            notes=data.get("notes", ""),
            stage_id=data.get("stage_id", ""),
            project_id=data.get("id", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def update(self, company_name=None, system_name=None, cert_number=None,
               issue_date=None, level=None, location=None,
               deadline=None, notes=None, stage_id=None):
        if company_name is not None: self.company_name = company_name
        if system_name is not None: self.system_name = system_name
        if cert_number is not None: self.cert_number = cert_number
        if issue_date is not None: self.issue_date = issue_date
        if level is not None: self.level = level
        if location is not None: self.location = location
        if deadline is not None: self.deadline = deadline
        if notes is not None: self.notes = notes
        if stage_id is not None: self.stage_id = stage_id
        self.updated_at = get_now_str()

    def __repr__(self) -> str:
        return f"Project(id={self.id}, name={self.name})"
