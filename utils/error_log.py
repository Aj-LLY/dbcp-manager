"""
错误日志模块 - 捕获全局异常并提供控制台查看界面。

将所有未处理的 Tkinter 异常和程序运行日志汇总，通过工具栏"控制台"按钮查看。
"""

import traceback
import datetime

_errors: list[str] = []


def capture(message: str):
    """记录一条错误/日志信息"""
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    _errors.append(f"[{ts}] {message}")
    if len(_errors) > 500:
        _errors.pop(0)


def capture_exception(exc_type, exc_value, exc_tb):
    """Tkinter 异常回调：捕获未处理异常"""
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    capture(tb_text)


def get_errors() -> str:
    """获取所有已记录的错误信息"""
    return "\n".join(_errors) if _errors else "暂无错误记录"


def install(root):
    """在 Tkinter 根窗口上安装全局异常捕获"""
    root.report_callback_exception = capture_exception
