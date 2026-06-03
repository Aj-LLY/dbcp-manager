"""
项目管理服务模块 - 处理等保测评项目的核心业务逻辑。

本模块在数据持久化层（DataService）之上提供语义化的项目管理接口，负责：
- 项目的增删改查（CRUD）操作
- 项目阶段变更（看板拖拽、箭头移动、详情编辑时的阶段切换）
- 输入数据校验（公司/系统名称合法性、证书编号格式校验）
- 操作日志自动记录（通过回调函数委托给 LogService）

本服务是连接 DataService 和 UI 层的关键桥梁，封装了所有项目相关的业务规则。
"""

# ---------------------------------------------------------------------------
# 标准库导入
# ---------------------------------------------------------------------------
from typing import Callable, Optional
# Callable: 用于标注回调函数的类型签名
# Optional: 用于标记可空返回值类型

# ---------------------------------------------------------------------------
# 项目内导入（模型层 + 数据层 + 工具层）
# ---------------------------------------------------------------------------
from models.project import Project
# 项目实体类，封装了项目的所有属性和序列化/反序列化逻辑

from services.data_service import DataService
# 数据持久化服务（单例），提供底层 JSON 文件的读写操作

from utils.helpers import validate_project_fields, validate_cert_number
# validate_project_fields: 校验公司名称和系统名称的合法性（非空、长度等）
# validate_cert_number: 校验证书编号格式（11位数字-5位数字）


class ProjectService:
    """项目管理服务。

    封装所有项目相关的业务逻辑，在 DataService 提供的纯数据操作之上
    添加业务校验、日志记录等语义化功能。

    对项目的所有写操作（创建、编辑、删除、阶段变更）都会自动记录操作日志，
    日志通过构造函数传入的 log_callback 回调函数异步记录，实现服务解耦。

    属性说明:
        _ds (DataService): 数据持久化服务引用（单例），用于底层数据读写。
        _log (Callable): 日志回调函数，签名为 (action, detail, **kwargs)，
                         实际指向 LogService.create_log_callback() 的返回值。
    """

    def __init__(self, data_service: DataService,
                 log_callback: Optional[Callable] = None):
        """初始化项目管理服务。

        Args:
            data_service: DataService 的单例实例，提供数据存取能力。
            log_callback: 操作日志回调函数，签名为 (action, detail, **kwargs)。
                          为 None 时使用空操作函数占位，不记录日志。
        """
        # 持有数据层的引用，所有数据操作最终都委托给它
        self._ds = data_service

        # 保存日志回调：None 时使用空 lambda 避免每次调用前的 None 检查
        # lambda *a, **kw: None 是一个接受任意参数但不做任何事的函数
        self._log = log_callback or (lambda *a, **kw: None)

    # ========================================================================
    # 查询操作（Read）
    # ========================================================================

    def get_all_projects(self) -> list[Project]:
        """获取所有项目的 Project 对象列表，按创建时间升序排列。

        从数据层获取原始字典数据后，将其转换为 Project 实体对象，
        并按 created_at 字段排序，最早创建的项目排在最前面。

        Returns:
            list[Project]: 按创建时间升序排列的 Project 对象列表。
        """
        # 从数据层获取所有项目的字典列表
        dicts = self._ds.get_all_projects()
        # 将每个字典转换为 Project 实体对象
        projects = [Project.from_dict(d) for d in dicts]
        # 按创建时间升序排列：先创建的项目显示在上方/前方
        return sorted(projects, key=lambda p: p.created_at)

    def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """根据项目ID获取单个 Project 对象。

        Args:
            project_id: 项目的唯一标识符。

        Returns:
            Project | None: 匹配的 Project 对象，未找到时返回 None。
        """
        # 从数据层查找原始字典（避免创建全部 Project 对象的开销）
        d = self._ds.get_project_by_id(project_id)
        # 找到则转换为对象，否则返回 None
        return Project.from_dict(d) if d else None

    def get_projects_by_stage(self, stage_id: str) -> list[Project]:
        """获取处于指定流程阶段的所有项目。

        用于看板视图中按列（阶段）展示项目卡片。遍历所有项目并过滤出
        stage_id 匹配的项目。

        Args:
            stage_id: 流程阶段的唯一标识符。

        Returns:
            list[Project]: 处于该阶段的所有 Project 对象列表。
        """
        # 过滤：遍历所有项目，只保留 stage_id 匹配的项目
        return [p for p in self.get_all_projects() if p.stage_id == stage_id]

    # ========================================================================
    # 增删改操作（Create / Update / Delete）
    # ========================================================================

    def create_project(self, company_name: str, system_name: str,
                       cert_number: str, issue_date: str, level: str,
                       location: str, deadline: str, notes: str,
                       stage_id: str) -> tuple[bool, str, Optional[Project]]:
        """创建新的等保测评项目。

        完整的创建流程：
        1. 校验公司/系统名称的合法性（非空、不全是空白等）。
        2. 如果填写了证书编号，校验其格式是否合法。
        3. 通过校验后，构建 Project 实体对象。
        4. 序列化后写入数据层。
        5. 记录"新增项目"操作日志。

        Args:
            company_name: 被测评单位的公司名称。
            system_name: 被测信息系统名称。
            cert_number: 备案证书编号（可选，为空时跳过格式校验）。
            issue_date: 证书颁发日期。
            level: 系统保护等级。
            location: 项目所在地。
            deadline: 项目截止日期。
            notes: 备注信息。
            stage_id: 初始流程阶段ID（通常为第一个阶段的ID）。

        Returns:
            tuple[bool, str, Project | None]:
                - bool: 操作是否成功。
                - str: 成功/失败的描述消息。
                - Project | None: 成功时返回创建的 Project 对象，失败时为 None。
        """
        # 步骤1: 校验公司名称和系统名称的合法性
        valid, msg = validate_project_fields(company_name, system_name)
        if not valid:
            return False, msg, None

        # 步骤2: 校验证书编号格式（仅当填写了证书编号时校验）
        valid, msg = validate_cert_number(cert_number)
        if not valid:
            return False, msg, None

        # 步骤3: 构建 Project 实体对象（去除所有字符串的首尾空白）
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

        # 步骤4: 将项目对象序列化为字典后写入数据层
        self._ds.add_project(project.to_dict())

        # 步骤5: 记录操作日志（通过回调函数写入，解耦日志服务）
        self._log(
            action="新增项目",
            detail=f"创建项目「{project.name}」",
            project_id=project.id,
            project_name=project.name,
        )

        # 返回成功结果和创建的项目对象
        return True, "项目创建成功", project

    def update_project(self, project_id: str, company_name: str = None,
                       system_name: str = None, cert_number: str = None,
                       issue_date: str = None, level: str = None,
                       location: str = None,
                       deadline: str = None, notes: str = None,
                       stage_id: str = None,
                       folder_path: str = None) -> tuple[bool, str]:
        """更新现有项目的部分字段（支持部分更新）。

        所有参数除 project_id 外均为可选（None 表示不更新该字段）。
        如果阶段发生了变化（stage_id 不同于旧值），自动记录"阶段变更"日志；
        否则记录"编辑项目"日志。

        Args:
            project_id: 要更新的项目唯一标识符（必填）。
            company_name: 新的公司名称（None 表示保持不变）。
            system_name: 新的系统名称（None 表示保持不变）。
            cert_number: 新的证书编号（None 表示保持不变）。
            issue_date: 新的颁发日期（None 表示保持不变）。
            level: 新的保护等级（None 表示保持不变）。
            location: 新的所在地（None 表示保持不变）。
            deadline: 新的截止日期（None 表示保持不变）。
            notes: 新的备注（None 表示保持不变）。
            stage_id: 新的阶段ID（None 表示保持不变）。
            folder_path: 新的文件夹路径（None 表示保持不变）。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
        # 先查找项目，确认存在
        project = self.get_project_by_id(project_id)
        if not project:
            return False, "项目不存在"

        # 如果修改了公司名称或系统名称，需要重新校验合法性
        if company_name is not None or system_name is not None:
            # 未传入的字段沿用当前值，保证校验时使用的是合并后的完整数据
            c = company_name if company_name is not None else project.company_name
            s = system_name if system_name is not None else project.system_name
            valid, msg = validate_project_fields(c, s)
            if not valid:
                return False, msg

        # 如果修改了证书编号，需要校验格式
        if cert_number is not None:
            valid, msg = validate_cert_number(cert_number)
            if not valid:
                return False, msg

        # 保存变更前的阶段ID，用于判断是否需要写入阶段变更日志
        old_stage_id = project.stage_id
        old_stage = self._get_stage_name(old_stage_id)

        # 执行项目属性的部分更新（Project.update 只更新非 None 的字段）
        project.update(company_name=company_name, system_name=system_name,
                       cert_number=cert_number, issue_date=issue_date,
                       level=level, location=location,
                       deadline=deadline, notes=notes, stage_id=stage_id,
                       folder_path=folder_path)

        # 将更新后的项目序列化并写入数据层
        self._ds.update_project(project_id, project.to_dict())

        # 根据是否包含阶段变更，记录不同类型的操作日志
        if stage_id is not None and stage_id != old_stage_id:
            # 阶段发生了变化：记录"阶段变更"日志（包含前后阶段名称）
            new_stage = self._get_stage_name(stage_id)
            self._log(
                action="阶段变更",
                detail=f"{project.name}：{old_stage} / {new_stage}",
                project_id=project.id,
                project_name=project.name,
                from_stage=old_stage,
                to_stage=new_stage,
            )
        else:
            # 非阶段变更：记录"编辑项目"日志
            self._log(
                action="编辑项目",
                detail=f"编辑项目「{project.name}」的信息",
                project_id=project.id,
                project_name=project.name,
            )

        return True, "项目更新成功"

    def delete_project(self, project_id: str) -> tuple[bool, str]:
        """删除指定项目（不可逆操作）。

        在删除前先查找项目以获取项目名称用于日志记录，
        然后从数据层执行实际删除。

        Args:
            project_id: 要删除的项目唯一标识符。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
        # 先查找项目，确认存在并获取名称（用于日志）
        project = self.get_project_by_id(project_id)
        if not project:
            return False, "项目不存在"

        # 从数据层删除项目
        self._ds.delete_project(project_id)

        # 记录删除操作日志
        self._log(
            action="删除项目",
            detail=f"删除项目「{project.name}」",
            project_id=project.id,
            project_name=project.name,
        )

        return True, f"项目「{project.name}」已删除"

    def move_project(self, project_id: str, new_stage_id: str) -> tuple[bool, str]:
        """将项目移动到新的流程阶段。

        本质上是 update_project 的特殊简化情况（仅修改 stage_id 字段）。
        内部直接复用 update_project 的完整逻辑，自动处理阶段变更日志记录。

        Args:
            project_id: 要移动的项目唯一标识符。
            new_stage_id: 目标流程阶段ID。

        Returns:
            tuple[bool, str]: (是否成功, 操作消息)。
        """
        # 委托给 update_project，只传入 stage_id 参数
        # update_project 内部会自动判断阶段是否变化并记录相应日志
        return self.update_project(project_id, stage_id=new_stage_id)

    # ========================================================================
    # 辅助方法（内部使用）
    # ========================================================================

    def _get_stage_name(self, stage_id: str) -> str:
        """根据阶段ID获取阶段的可读名称。

        用于日志中展示人类可读的阶段名而非原始ID。
        遍历 DataService 中的流程阶段列表进行查找。

        Args:
            stage_id: 流程阶段唯一标识符。

        Returns:
            str: 阶段名称，找不到对应阶段时返回"未知阶段"。
        """
        for s in self._ds.get_all_stages():
            if s.get("id") == stage_id:
                # 找到匹配阶段：返回其名称
                return s.get("name", "")
        # ID 不匹配任何已有阶段（如阶段已被删除）
        return "未知阶段"
