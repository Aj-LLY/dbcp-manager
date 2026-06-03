"""
通用辅助函数模块 - 提供日期格式化、ID生成、字符串处理、输入验证、UI组件等通用工具

本模块是一组纯函数工具集，无状态、无副作用，可在整个项目的任何层级安全调用。

功能分类：
  1. ID 生成（generate_id）：基于毫秒级时间戳生成唯一标识符
  2. 日期处理（format_date / get_today_str / get_now_str / days_between / days_until_deadline）
  3. 字符串处理（truncate_text / safe_strip）
  4. 输入验证（validate_project_name / validate_project_fields / validate_cert_number）
  5. UI 组件（bordered_entry）：创建带四边灰色边框的 Tkinter 输入框

依赖：
  - time / datetime / re：Python 标准库
  - tkinter：Python 标准 GUI 库

设计原则：
  - 纯函数：不依赖外部状态，相同输入得到相同输出
  - 容错设计：解析失败时返回安全的默认值，不抛出异常
  - 独立性强：不依赖项目其他模块
"""

# =============================================================================
# 导入区
# =============================================================================

import time  # 时间模块，提供 time.time() 获取毫秒级 Unix 时间戳用于生成唯一 ID
import tkinter as tk  # Python 标准 GUI 库，用于创建带边框的输入框等自定义组件
import re  # 正则表达式模块，用于字符串格式验证（证书编号等）
from datetime import datetime, date  # 日期时间模块，提供日期解析、格式化、差值计算等功能


# =============================================================================
# ID 生成工具
# =============================================================================

def generate_id(prefix: str = "") -> str:
    """基于毫秒级时间戳生成唯一标识符

    生成的 ID 格式为：{前缀}_{毫秒时间戳}（如果有前缀）或纯时间戳。
    毫秒级精度确保在同一次运行中不会产生重复 ID。

    使用示例：
      - generate_id("proj")  -> "proj_1717372800123"  （项目 ID）
      - generate_id("stage") -> "stage_1717372800456" （阶段 ID）

    Args:
        prefix: 可选 ID 前缀，用于区分不同类型实体（如 "proj" = 项目，"stage" = 阶段）

    Returns:
        str: 唯一的标识符字符串
    """
    ts = str(int(time.time() * 1000))  # 获取当前 Unix 时间戳（秒）-> 乘以 1000 转毫秒 -> 取整 -> 转字符串
    return f"{prefix}_{ts}" if prefix else ts  # 有前缀时拼接：prefix_timestamp，否则直接返回时间戳


# =============================================================================
# 日期处理工具
# =============================================================================

def format_date(date_str: str, fmt: str = "%Y-%m-%d") -> str:
    """将日期字符串转换为指定格式

    用于统一日期显示格式，例如将系统存储的 YYYY-MM-DD 格式转换为
    用户偏好的 YYYY年MM月DD日 格式。

    Args:
        date_str: 原始日期字符串（标准 YYYY-MM-DD 格式）
        fmt: 目标输出格式（默认 "%Y-%m-%d"）

    Returns:
        str: 格式化后的日期字符串；解析失败则返回原始字符串（容错处理）
    """
    if not date_str:  # 空字符串
        return ""  # 直接返回空字符串
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")  # 按标准 ISO 格式解析为 datetime 对象
        return dt.strftime(fmt)  # 按目标格式重新格式化输出
    except ValueError:  # 日期字符串不符合 "%Y-%m-%d" 格式（如 "2026/06/03" 或非法值）
        return date_str  # 容错处理：返回原始字符串，避免崩溃


def get_today_str() -> str:
    """获取今天的日期字符串（YYYY-MM-DD 格式）

    Returns:
        str: 当前日期，如 "2026-06-03"
    """
    return date.today().strftime("%Y-%m-%d")  # 获取今天日期 -> 格式化为 YYYY-MM-DD


def get_now_str() -> str:
    """获取当前日期时间字符串（YYYY-MM-DD HH:MM:SS 格式）

    Returns:
        str: 当前时间戳，如 "2026-06-03 14:30:25"
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 获取当前时间 -> 格式化为标准格式


def days_between(date_str1: str, date_str2: str) -> int:
    """计算两个日期字符串之间的天数差

    既可以计算未来（正数）也可以计算过去（负数），适用场景包括：
      - 统计项目实际完成耗时（完成日期 - 开始日期 = 正数）
      - 评估任务是否按时完成（交付日期 - 截止日期 = 负数表示提前）

    Args:
        date_str1: 日期字符串1（被减数，如"2026-06-10"）
        date_str2: 日期字符串2（减数，如"2026-06-03"）

    Returns:
        int: 天数差（date_str1 - date_str2），解析失败返回 0
    """
    try:
        d1 = datetime.strptime(date_str1, "%Y-%m-%d").date()  # 解析第一个日期 -> date 对象
        d2 = datetime.strptime(date_str2, "%Y-%m-%d").date()  # 解析第二个日期 -> date 对象
        return (d1 - d2).days  # 计算 timedelta 对象的天数分量
    except (ValueError, TypeError):  # 任一日期的格式错误或类型不匹配
        return 0  # 返回 0 表示无法计算，避免向上层抛出异常


def days_until_deadline(deadline_str: str) -> int:
    """计算距离截止日期还有多少天

    这是 days_between 的快捷封装，专用于计算截止日期的剩余天数。

    Args:
        deadline_str: 项目截止日期字符串（YYYY-MM-DD 格式）

    Returns:
        int: 剩余天数（截止日期 - 今天），正数 = 未到期，负数 = 已过期
    """
    return days_between(deadline_str, get_today_str())  # 截止日 - 今天 = 剩余天数


# =============================================================================
# 字符串处理工具
# =============================================================================

def truncate_text(text: str, max_length: int = 50) -> str:
    """截断过长文本，超出部分用省略号替代

    用于在卡片、表格等有限空间内显示长文本。

    Args:
        text: 原始文本内容
        max_length: 允许的最大字符数（含省略号的 3 个字符）

    Returns:
        str: 截断后的文本（超长时末尾添加 "..."）
    """
    if len(text) <= max_length:  # 文本长度未超过限制
        return text  # 直接返回原文
    return text[:max_length - 3] + "..."  # 截断前 max_length-3 个字符，追加 "..."（3 个字符）


def safe_strip(text: str) -> str:
    """安全去除首尾空白字符，处理 None 值

    普通的 text.strip() 在 text 为 None 时会抛出 AttributeError。
    此函数先检查 None，避免异常传播。

    Args:
        text: 原始字符串（可能为 None）

    Returns:
        str: 去除首尾空白后的字符串，None 返回空字符串 ""
    """
    if text is None:  # None 值处理（防止 AttributeError）
        return ""  # None 视为空字符串
    return text.strip()  # 正常字符串：去除首尾空白字符


# =============================================================================
# 输入验证工具
# =============================================================================

def validate_project_name(name: str) -> tuple[bool, str]:
    """验证单个项目名称字段的合法性

    检查规则：
      1. 非空：名称不能为空或仅含空白字符
      2. 长度限制：不超过 50 个字符
      3. 特殊字符：禁止包含文件系统和 XML 中的危险字符（< > : " / \\ | ? *）

    Args:
        name: 要验证的名称字段值

    Returns:
        tuple[bool, str]: (是否合法, 错误消息)，合法时消息为空字符串
    """
    if not name or not name.strip():  # 名称为空或全为空白字符
        return False, "名称不能为空"  # 验证失败：空值错误

    if len(name.strip()) > 50:  # 去除空白后的实际长度超过 50 字符
        return False, "名称不能超过50个字符"  # 验证失败：长度超限

    if re.search(r'[<>:"/\\|?*]', name):  # 使用正则检查是否包含文件系统的非法字符
        return False, "名称不能包含特殊字符: < > : \" / \\ | ? *"  # 验证失败：特殊字符

    return True, ""  # 验证通过，返回成功标志和空错误消息


def validate_project_fields(company_name: str, system_name: str) -> tuple[bool, str]:
    """验证公司名称和系统名称的合法性（至少填写一个）

    等保测评项目以"公司名称 + 系统名称"作为标识组合，
    至少需要一个字段非空才能唯一标识项目。

    验证流程：
      1. 检查至少一个字段非空
      2. 对非空字段分别执行 validate_project_name 验证

    Args:
        company_name: 客户公司名称
        system_name: 被测系统名称

    Returns:
        tuple[bool, str]: (是否合法, 错误消息)
    """
    c = (company_name or "").strip()  # 处理 None -> "" + 去空白
    s = (system_name or "").strip()   # 处理 None -> "" + 去空白

    if not c and not s:  # 两个字段都为空
        return False, "公司名称和系统名称至少需要填写一个"  # 验证失败

    for label, val in [("公司名称", c), ("系统名称", s)]:  # 逐一检查非空字段
        if val:  # 该字段有值（非 ""）
            ok, msg = validate_project_name(val)  # 调用单项验证
            if not ok:  # 单项不通过
                return False, f"{label}{msg}"  # 拼接字段名 + 具体错误信息
    return True, ""  # 全部通过


def validate_cert_number(number: str) -> tuple[bool, str]:
    """验证证书/备案编号格式是否合法

    规范格式：11 位数字，一个连字符(-)，再加 5 位数字
    示例：12345678901-00001

    允许空值（表示该项目尚未备案），空值直接返回验证通过。

    Args:
        number: 证书编号字符串

    Returns:
        tuple[bool, str]: (是否合法, 错误消息)
    """
    if not number or not number.strip():  # 空值或空白
        return True, ""  # 允许空值（未备案状态），验证通过

    n = number.strip()  # 去除首尾空白
    if len(n) != 17:  # 总长度必须为 17（11 + 1 + 5）
        return False, "证书编号应为17位（11位数字-5位数字）"

    if not re.match(r'^\d{11}-\d{5}$', n):  # 正则验证：11 位数字 - 5 位数字
        return False, "证书编号格式错误：应为11位数字-5位数字，如 12345678901-00001"

    return True, ""  # 验证通过


# =============================================================================
# UI 组件工具
# =============================================================================

def bordered_entry(parent, font=None, **entry_kwargs):
    """创建带四边 1px 灰色边框的 Tkinter 输入框

    通过嵌套两层 Frame 实现边框效果：
      外层 Frame（灰色 = 边框颜色）+ 内层 Frame（白色 = 输入区背景，留 1px 边距）
      内层 Frame 中的 Entry 组件无边框，整体呈现统一灰色边框效果。

    这种实现方式比直接设置 Entry 的 highlightthickness 更可控，
    且边框颜色和粗细由外层 Frame 完全控制，不受主题影响。

    Args:
        parent: 父级 Tkinter 容器（如 Frame、Toplevel、Tk 等）
        font: 输入框字体设置，格式为 (字体名, 字号) 元组，默认微软雅黑 10 号
        **entry_kwargs: 传递给 tk.Entry 的其他参数，如 textvariable=var、width=30 等

    Returns:
        tuple: (entry, outer_frame)
          - entry: tk.Entry 实例，可用于绑定事件、读取值
          - outer_frame: 外层 Frame 实例，用于布局（pack/grid）
    """
    outer = tk.Frame(parent, bg="#d0d5dd")  # 外层框架：灰色背景作为边框
    inner = tk.Frame(outer, bg="#ffffff")   # 内层框架：白色背景作为输入区域
    inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)  # 内外层留 1px 边距，形成边框视觉效果

    if font is None:  # 未指定字体时使用项目默认配置
        font = ("Microsoft YaHei", 10)  # 默认字体：微软雅黑 10 号

    entry = tk.Entry(inner, font=font, relief="flat", borderwidth=0, **entry_kwargs)  # 创建无边框输入框
    entry.pack(fill=tk.BOTH, expand=True, ipady=2)  # 水平+垂直填充，2px 垂直内边距
    return entry, outer  # 返回输入框和外层容器供调用方布局
