"""
项目管理服务 - 处理项目的增删改查和进度变更业务逻辑

负责：
- 项目CRUD操作（创建、读取、更新、删除）
- 项目阶段变更（拖拽移动）
- 数据校验（名称合法性检查）
- 操作日志记录（通过回调函数委托给日志服务）
"""

from typing import Optional, Callable  # 类型提示：Optional表示可空值，Callable表示可调用对象
from models.project import Project  # 导入项目实体类
from services.data_service import DataService  # 导入数据持久化服务
from utils.helpers import validate_project_fields, validate_cert_number  # 导入项目字段验证函数


class ProjectService:
    """项目管理服务
    封装所有项目相关的业务逻辑，在数据服务（DataService）之上提供语义化的操作接口。
    对项目的所有写操作都会自动记录操作日志。
    """

    def __init__(self, data_service: DataService,
                 log_callback: Optional[Callable] = None):
        """初始化项目管理服务

        Args:
            data_service: 数据持久化服务实例（单例）
            log_callback: 操作日志回调函数，签名为 (action, detail, **kwargs)
                          为None时使用空函数占位，不记录日志
        """
        self._ds = data_service  # 持有数据服务引用
        # 保存日志回调，None时使用空lambda避免后续None检查
        self._log = log_callback or (lambda *a, **kw: None)

    # ==================== 查询操作 ====================

    def get_all_projects(self) -> list[Project]:
        """获取所有项目列表，按创建时间排序（最早创建的在前面）"""
        dicts = self._ds.get_all_projects()  # 从数据服务获取原始字典列表
        projects = [Project.from_dict(d) for d in dicts]  # 将每个字典转换为Project对象
        return sorted(projects, key=lambda p: p.created_at)  # 按创建时间排序

    def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """根据ID获取单个项目

        Args:
            project_id: 项目唯一标识

        Returns:
            Project对象，未找到返回None
        """
        d = self._ds.get_project_by_id(project_id)  # 从数据层查找项目字典
        return Project.from_dict(d) if d else None  # 找到则转换为Project对象，否则返回None

    def get_projects_by_stage(self, stage_id: str) -> list[Project]:
        """获取处于指定阶段的所有项目
        用于看板视图中按列展示项目卡片

        Args:
            stage_id: 流程阶段ID

        Returns:
            处于该阶段的所有Project对象列表
        """
        return [p for p in self.get_all_projects() if p.stage_id == stage_id]  # 过滤出指定阶段的项目

    # ==================== 增删改操作 ====================

    def create_project(self, company_name: str, system_name: str,
                       cert_number: str, issue_date: str, level: str,
                       location: str, deadline: str, notes: str,
                       stage_id: str) -> tuple[bool, str, Optional[Project]]:
        """创建新项目"""
        valid, msg = validate_project_fields(company_name, system_name)
        if not valid:
            return False, msg, None
        valid, msg = validate_cert_number(cert_number)
        if not valid:
            return False, msg, None
        project = Project(
            company_name=(company_name or "").strip(),
            system_name=(system_name or "").strip(),
            cert_number=(cert_number or "").strip(),
            issue_date=(issue_date or "").strip(),
            level=(level or "").strip(),
            location=(location or "").strip(),
            deadline=deadline,
            notes=notes,
            stage_id=stage_id,
        )
        self._ds.add_project(project.to_dict())  # 将项目序列化后添加到数据层

        self._log(  # 记录操作日志
            action="新增项目",
            detail=f"创建项目「{project.name}」",
            project_id=project.id,
            project_name=project.name,
        )
        return True, "项目创建成功", project  # 返回成功及创建的Project对象

    def update_project(self, project_id: str, company_name: str = None,
                       system_name: str = None, cert_number: str = None,
                       issue_date: str = None, level: str = None,
                       location: str = None,
                       deadline: str = None, notes: str = None,
                       stage_id: str = None) -> tuple[bool, str]:
        """更新项目信息（支持部分更新）"""
        project = self.get_project_by_id(project_id)  # 查找项目
        if not project:  # 项目不存在
            return False, "项目不存在"

        if company_name is not None or system_name is not None:  # 如果修改了名称字段
            c = company_name if company_name is not None else project.company_name
            s = system_name if system_name is not None else project.system_name
            valid, msg = validate_project_fields(c, s)
            if not valid:
                return False, msg

        if cert_number is not None:
            valid, msg = validate_cert_number(cert_number)
            if not valid:
                return False, msg

        old_stage_id = project.stage_id  # 保存变更前的阶段ID（用于日志判断）
        old_stage = self._get_stage_name(old_stage_id)  # 变更前的阶段名称
        project.update(company_name=company_name, system_name=system_name,
                       cert_number=cert_number, issue_date=issue_date,
                       level=level, location=location,
                       deadline=deadline, notes=notes, stage_id=stage_id)
        self._ds.update_project(project_id, project.to_dict())  # 将更新后的项目持久化

        if stage_id is not None and stage_id != old_stage_id:  # 阶段发生了变化
            new_stage = self._get_stage_name(stage_id)
            self._log(  # 记录阶段变更日志
                action="阶段变更",
                detail=f"{project.name}：{old_stage} → {new_stage}",
                project_id=project.id,
                project_name=project.name,
                from_stage=old_stage,
                to_stage=new_stage,
            )
        else:  # 其他编辑操作（非阶段变更）
            self._log(  # 记录编辑日志
                action="编辑项目",
                detail=f"编辑项目「{project.name}」的信息",
                project_id=project.id,
                project_name=project.name,
            )
        return True, "项目更新成功"

    def delete_project(self, project_id: str) -> tuple[bool, str]:
        """删除项目

        Args:
            project_id: 要删除的项目ID

        Returns:
            (是否成功, 消息)
        """
        project = self.get_project_by_id(project_id)  # 先查找项目（获取名称用于日志）
        if not project:  # 项目不存在
            return False, "项目不存在"

        self._ds.delete_project(project_id)  # 从数据层删除项目

        self._log(  # 记录删除日志
            action="删除项目",
            detail=f"删除项目「{project.name}」",
            project_id=project.id,
            project_name=project.name,
        )
        return True, f"项目「{project.name}」已删除"

    def move_project(self, project_id: str, new_stage_id: str) -> tuple[bool, str]:
        """将项目移动到新阶段
        本质上是 update_project 的特殊情况（仅修改stage_id），
        内部复用 update_project 逻辑，自动记录阶段变更日志

        Args:
            project_id: 项目ID
            new_stage_id: 目标阶段ID

        Returns:
            (是否成功, 消息)
        """
        return self.update_project(project_id, stage_id=new_stage_id)  # 委托给update_project，只传stage_id

    # ==================== 辅助方法 ====================

    def _get_stage_name(self, stage_id: str) -> str:
        """根据阶段ID获取阶段名称
        用于日志中展示可读的阶段名而非原始ID

        Args:
            stage_id: 流程阶段ID

        Returns:
            阶段名称，找不到则返回"未知阶段"
        """
        for s in self._ds.get_all_stages():  # 遍历所有流程阶段
            if s.get("id") == stage_id:  # 匹配阶段ID
                return s.get("name", "")  # 返回阶段名称
        return "未知阶段"  # ID不匹配任何阶段，返回默认文本
