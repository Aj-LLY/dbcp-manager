"""
项目对话框 OCR 备案证识别模块 -- 等保测评进度管理系统

本模块将 OCR 备案证识别的相关逻辑从 ProjectDialog 中抽取为独立的
单函数，以 dialog 实例作为第一个参数，保持所有原有行为不变。

函数列表：
  - on_upload_cert(dialog): 上传备案证文件并启动后台 OCR 线程
  - fill_cert_result(dialog, result, file_path): 将 OCR 识别结果填充到表单
  - archive_cert_file(dialog, src_path): 将备案证文件复制到项目归档目录
  - ocr_failed(dialog, error): OCR 识别失败后的恢复与提示处理
"""

import os
import shutil
import threading
from tkinter import filedialog


def on_upload_cert(dialog):
    """上传备案证文件并启动后台线程进行 OCR 识别。

    打开文件选择对话框让用户选择备案证图片或 PDF 文件，
    选中后在后台线程中调用 CertOCRService 进行识别，
    识别结果通过 after 回调回主线程更新表单字段。

    支持的文件格式：PDF、PNG、JPG、JPEG、BMP。
    """
    # 打开文件选择对话框，筛选图片和 PDF 文件
    file_path = filedialog.askopenfilename(
        parent=dialog,
        title="选择备案证文件",
        filetypes=[
            ("图片和PDF文件", "*.pdf *.png *.jpg *.jpeg *.bmp"),
            ("PDF文件", "*.pdf"),
            ("图片文件", "*.png *.jpg *.jpeg *.bmp"),
        ],
    )
    if not file_path:
        return  # 用户取消选择，直接返回

    # 禁用上传按钮并显示识别中状态
    dialog._upload_btn.configure(state="disabled", text="识别中...")
    dialog._ocr_status.configure(text="正在识别备案证，请稍候...", fg="#f39c12")

    def _run():
        """后台线程执行函数：调用 OCR 服务并回传结果到主线程。"""
        try:
            from services.cert_ocr import CertOCRService
            result = CertOCRService().recognize(file_path)
            dialog.after(0, lambda: fill_cert_result(dialog, result, file_path))
        except Exception as e:
            dialog.after(0, lambda: ocr_failed(dialog, str(e)))

    # 启动后台线程执行识别（daemon 线程，随主程序退出自动终止）
    threading.Thread(target=_run, daemon=True).start()


def fill_cert_result(dialog, result: dict, file_path: str = ""):
    """将 OCR 识别结果填充到表单字段，并将备案证文件归档。

    恢复上传按钮，更新各输入框，并将原始文件复制到
    01-其他归档文件/01-备案证-往期测评报告/ 目录下。

    Args:
        dialog: ProjectDialog 实例。
        result: OCR 识别结果字典，可能包含的键：
            company_name, system_name, cert_number, issue_date, level
        file_path: 备案证源文件路径，用于后续归档。
    """
    dialog._upload_btn.configure(state="normal", text="上传备案证识别")  # 恢复按钮
    # 如果识别结果所有值都为空，提示用户手动填写
    if not any(result.values()):
        dialog._ocr_status.configure(text="未识别到有效信息，请手动填写", fg="#e74c3c")
        return

    # 逐个字段填充到对应输入框，并记录已填充的字段名
    filled = []
    if result.get("company_name"):
        dialog._company_var.set(result["company_name"]); filled.append("公司名称")
    if result.get("system_name"):
        dialog._system_var.set(result["system_name"]); filled.append("系统名称")
    if result.get("cert_number"):
        dialog._cert_var.set(result["cert_number"]); filled.append("证书编号")
    if result.get("issue_date"):
        dialog._issue_date_var.set(result["issue_date"]); filled.append("下证日期")
    if result.get("level"):
        dialog._level_var.set(result["level"]); filled.append("系统等级")

    # 更新 OCR 状态标签
    dialog._ocr_status.configure(
        text=f"已识别：{'、'.join(filled)}（请核对）" if filled else "识别结果不完整",
        fg="#27ae60" if filled else "#e67e22",
    )

    # 归档备案证文件到项目文件夹
    if file_path and filled:
        archive_cert_file(dialog, file_path)


def archive_cert_file(dialog, src_path: str, row_idx: int = 0):
    """将备案证文件重命名并移动到项目文件夹。

    文件命名: {公司}-{系统}-{证书编号}.{ext}
    多系统: 移动到 {root}/{系统名称}/
    单系统: 移动到 {root}/
    """
    try:
        root = dialog._folder_path_var.get().strip()
        if not root or not os.path.isdir(root):
            return
        cname = dialog._company_var.get().strip()
        if not cname:
            return
        # 获取当前系统行数据
        sys_rows = getattr(dialog, '_sys_rows_list', [])
        if sys_rows and row_idx < len(sys_rows):
            r = sys_rows[row_idx]
            sname = r["system_var"].get().strip()
            cert = r["cert_var"].get().strip()
        else:
            sname = dialog._system_var.get().strip()
            cert = dialog._cert_var.get().strip()
        ext = os.path.splitext(src_path)[1] or ".pdf"
        cert_part = cert or "未备案"
        safe_name = f"{cname}-{sname or '未命名'}-{cert_part}{ext}"
        safe_name = safe_name.replace("/", "_").replace("\\", "_").replace(":", "_")
        # 多系统→子目录, 单系统→根目录
        if len(sys_rows) > 1 and sname:
            dest_dir = os.path.join(root, sname)
        else:
            dest_dir = root
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, safe_name)
        if not os.path.exists(dest_path):
            shutil.copy2(src_path, dest_path)
    except OSError:
        pass


def ocr_failed(dialog, error: str):
    """OCR 识别失败处理：恢复按钮并显示详细错误。"""
    dialog._upload_btn.configure(state="normal", text="上传备案证识别")
    detail = error[:120] if len(error) > 120 else error
    dialog._ocr_status.configure(text=f"识别失败：{detail}", fg="#e74c3c")
    # 记录到全局错误日志
    try:
        from utils.error_log import capture
        capture(f"OCR识别失败: {error}")
    except Exception:
        pass
