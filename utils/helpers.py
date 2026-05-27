"""
通用辅助函数模块 - 提供日期格式化、ID生成、字符串处理、UI组件等通用工具
"""

import time  # 时间模块，用于获取时间戳生成唯一ID
import tkinter as tk  # Python标准GUI库，用于创建自定义UI组件
import re  # 正则表达式模块，用于字符串验证
from datetime import datetime, date  # 日期时间模块，用于日期处理和格式化


def generate_id(prefix: str = "") -> str:
    """基于时间戳生成唯一标识ID

    Args:
        prefix: 可选ID前缀，用于区分不同类型实体（如 "proj" 表示项目，"stage" 表示阶段）

    Returns:
        格式为 {prefix}_{timestamp} 的唯一标识字符串
    """
    ts = str(int(time.time() * 1000))  # 获取当前Unix时间戳（毫秒级），转为整数再转为字符串
    return f"{prefix}_{ts}" if prefix else ts  # 有前缀则拼接前缀，无前缀直接返回时间戳


def format_date(date_str: str, fmt: str = "%Y-%m-%d") -> str:
    """格式化日期字符串为目标格式

    Args:
        date_str: 原始日期字符串（YYYY-MM-DD格式）
        fmt: 目标输出格式

    Returns:
        格式化后的日期字符串，如果解析失败则返回原字符串
    """
    if not date_str:  # 空字符串则直接返回空字符串
        return ""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")  # 按标准格式解析日期字符串
        return dt.strftime(fmt)  # 按目标格式重新格式化并返回
    except ValueError:  # 解析失败（日期格式不合法）
        return date_str  # 容错处理：返回原始字符串


def get_today_str() -> str:
    """获取今天的日期字符串 (YYYY-MM-DD)"""
    return date.today().strftime("%Y-%m-%d")  # 获取当前日期并按格式转为字符串


def get_now_str() -> str:
    """获取当前时间的日期时间字符串 (YYYY-MM-DD HH:MM:SS)"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 获取当前日期时间并按格式转为字符串


def days_between(date_str1: str, date_str2: str) -> int:
    """计算两个日期字符串之间的天数差

    Args:
        date_str1: 日期字符串1（被减数）
        date_str2: 日期字符串2（减数）

    Returns:
        天数差（date_str1 - date_str2，可能有负值），解析失败返回0
    """
    try:
        d1 = datetime.strptime(date_str1, "%Y-%m-%d").date()  # 解析第一个日期字符串为date对象
        d2 = datetime.strptime(date_str2, "%Y-%m-%d").date()  # 解析第二个日期字符串为date对象
        return (d1 - d2).days  # 计算日期差并返回天数部分
    except (ValueError, TypeError):  # 解析或类型错误时的容错处理
        return 0  # 返回0表示无法计算


def days_until_deadline(deadline_str: str) -> int:
    """计算距离截止日期还有多少天

    Args:
        deadline_str: 项目截止日期字符串（YYYY-MM-DD）

    Returns:
        剩余天数（截止日期 - 今天），正数表示未到期，负数表示已过期
    """
    return days_between(deadline_str, get_today_str())  # 用截止日期减去今天的日期得到剩余天数


def truncate_text(text: str, max_length: int = 50) -> str:
    """截断文本，超出部分用省略号替代

    Args:
        text: 原始文本内容
        max_length: 允许的最大字符数

    Returns:
        截断后的文本（超过最大长度时末尾添加"..."）
    """
    if len(text) <= max_length:  # 文本长度未超限
        return text  # 直接返回原文
    return text[:max_length - 3] + "..."  # 截断并添加三个点的省略号


def safe_strip(text: str) -> str:
    """安全去除空白字符，处理None值
    避免对None调用strip()导致AttributeError异常
    """
    if text is None:  # 处理None值
        return ""  # None返回空字符串
    return text.strip()  # 正常字符串去除首尾空白


def validate_project_name(name: str) -> tuple[bool, str]:
    """验证单个名称字段是否合法
    检查名称是否为空、长度是否超限、是否包含非法字符
    """
    if not name or not name.strip():  # 名称为空或仅含空白字符
        return False, "名称不能为空"  # 返回验证失败及原因
    if len(name.strip()) > 50:  # 名称长度超过50个字符
        return False, "名称不能超过50个字符"  # 返回长度超限提示
    if re.search(r'[<>:"/\\|?*]', name):  # 检查是否包含文件系统和XML中的特殊字符
        return False, "名称不能包含特殊字符: < > : \" / \\ | ? *"  # 返回特殊字符提示
    return True, ""  # 验证通过，返回成功标志和空消息


def validate_project_fields(company_name: str, system_name: str) -> tuple[bool, str]:
    """验证公司名称和系统名称至少有一个不为空
    等保测评项目中，公司名称和系统名称作为项目的标识组合，至少需要填写一个
    """
    c = (company_name or "").strip()  # 处理公司名称为None的情况并去除空白
    s = (system_name or "").strip()   # 处理系统名称为None的情况并去除空白

    if not c and not s:  # 两个字段都为空
        return False, "公司名称和系统名称至少需要填写一个"  # 返回验证失败

    for label, val in [("公司名称", c), ("系统名称", s)]:  # 遍历两个字段分别进行单项验证
        if val:  # 字段有值时进行验证
            ok, msg = validate_project_name(val)  # 调用单项名称验证函数
            if not ok:  # 单项验证不通过
                return False, f"{label}{msg}"  # 拼接字段标签和错误信息后返回
    return True, ""  # 所有验证通过


def bordered_entry(parent, font=None, **entry_kwargs):
    """创建带四边 1px 灰色边框的输入框，返回 (entry, outer_frame)
    通过嵌套Frame实现边框效果，适用于需要统一边框样式的输入组件

    Args:
        parent: 父级Tkinter容器
        font: 输入框字体设置，默认为微软雅黑10号
        **entry_kwargs: 传递给tk.Entry的其他参数（如宽度、文本变量等）

    Returns:
        (entry, outer_frame) 元组：输入框对象和外层容器框架
    """
    outer = tk.Frame(parent, bg="#d0d5dd")  # 外层框架设为灰色作为边框色
    inner = tk.Frame(outer, bg="#ffffff")   # 内层框架设为白色作为输入区域背景
    inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)  # 内层留1像素边距形成边框效果
    if font is None:  # 未指定字体时使用默认值
        font = ("Microsoft YaHei", 10)  # 默认字体：微软雅黑，10号
    entry = tk.Entry(inner, font=font, relief="flat", borderwidth=0, **entry_kwargs)  # 创建无边框的输入框
    entry.pack(fill=tk.BOTH, expand=True, ipady=2)  # 输入框填充并给一点内边距
    return entry, outer  # 返回输入框和外层框架供调用方布局使用
