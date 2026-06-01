"""
备案证 OCR 识别服务 - 上传备案证 PDF/图片，自动提取关键字段

支持识别《网络安全等级保护备案证明》中的：
- 证书编号（格式 11位数字-5位数字）
- 公司名称（备案单位）
- 系统名称
- 系统等级（第二级等）
- 证书下发时间

依赖（可选）: pip install easyocr PyMuPDF
"""

import os
import re
import tempfile
from typing import Optional


class CertOCRService:
    """备案证 OCR 识别服务（单例模式）

    使用 easyocr 进行中文 OCR 识别，PyMuPDF 处理 PDF 文件。
    Reader 初始化耗时较长，使用单例复用。
    """

    _instance: Optional["CertOCRService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._reader = None  # lazy init

    def _get_reader(self):
        """延迟初始化 easyocr Reader（首次调用时才加载模型）

        easyocr 为可选依赖，EXE 版本中可能未安装。
        """
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(["ch_sim", "en"], gpu=False)
            except ImportError:
                raise RuntimeError(
                    "OCR 识别功能需要安装 easyocr 和 PyTorch。\n"
                    "请执行: pip install easyocr PyMuPDF"
                )
        return self._reader

    def recognize(self, file_path: str) -> dict:
        """识别备案证文件，提取关键字段

        Args:
            file_path: PDF 或图片文件路径

        Returns:
            dict: 包含识别结果，字段为 company_name, system_name,
                  cert_number, deadline, level，识别失败对应值为空字符串
        """
        if not os.path.exists(file_path):
            return self._empty_result()

        try:
            img_bytes = self._file_to_image(file_path)
            texts = self._ocr_texts(img_bytes)
            return self._extract_fields(texts)
        except Exception:
            return self._empty_result()

    def _file_to_image(self, file_path: str) -> bytes:
        """将 PDF 或图片文件转为 PNG 字节数据"""
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            try:
                import fitz
            except ImportError:
                raise RuntimeError(
                    "PDF 文件识别需要安装 PyMuPDF。\n"
                    "请执行: pip install PyMuPDF\n"
                    "或使用 PNG/JPG 图片格式。"
                )
            doc = fitz.open(file_path)
            page = doc[0]
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            doc.close()
            return img_bytes
        else:
            with open(file_path, "rb") as f:
                return f.read()

    def _ocr_texts(self, img_bytes: bytes) -> list[str]:
        """对图片执行 OCR，返回识别文本列表（按置信度过滤）"""
        reader = self._get_reader()
        results = reader.readtext(img_bytes)
        return [text for _, text, conf in results if conf > 0.3]

    def _extract_fields(self, texts: list[str]) -> dict:
        """从 OCR 文本列表中提取结构化字段"""
        full_text = "\n".join(texts)

        return {
            "company_name": self._extract_company(texts),
            "system_name": self._extract_system_name(texts),
            "cert_number": self._extract_cert_number(full_text),
            "deadline": self._extract_date(full_text),
            "level": self._extract_level(full_text),
        }

    def _extract_cert_number(self, text: str) -> str:
        """提取证书编号：11位数字-5位数字"""
        m = re.search(r"\d{11}-\d{5}", text)
        return m.group(0) if m else ""

    def _extract_company(self, texts: list[str]) -> str:
        """提取公司名称：位于'单位'关键词之前的连续中文"""
        for i, t in enumerate(texts):
            t_clean = t.strip()
            if "单位" in t_clean and i > 0:
                prev = texts[i - 1].strip()
                if re.match(r"^[\u4e00-\u9fa5()（）]{2,30}$", prev):
                    return prev
            if "的:" in t_clean:
                before = t_clean.split("的:")[0]
                if re.search(r"公司$", before):
                    return before
        return ""

    def _extract_system_name(self, texts: list[str]) -> str:
        """提取系统名称：位于'系统'关键词之前的文本"""
        for i, t in enumerate(texts):
            t_clean = t.strip()
            if "系统" in t_clean:
                idx = t_clean.find("系统")
                if idx > 0:
                    name = t_clean[:idx]
                    name = re.sub(r"[.。的，,]$", "", name).strip()
                    if len(name) >= 2:
                        return name
                if idx <= 1 and i > 0:
                    prev = texts[i - 1].strip()
                    if len(prev) >= 2 and not re.match(r"^[第\d]", prev):
                        return prev
        return ""

    def _extract_level(self, text: str) -> str:
        """提取系统等级：第X级"""
        m = re.search(r"第[一二三四五\d]\s*级", text)
        if m:
            return m.group(0).replace(" ", "")
        return ""

    def _extract_date(self, text: str) -> str:
        """提取证书下发时间：YYYY年MM月DD日，转为 YYYY-MM-DD"""
        m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
        if m:
            y, mo, d = m.groups()
            return f"{y}-{int(mo):02d}-{int(d):02d}"
        return ""

    def _empty_result(self) -> dict:
        return {
            "company_name": "",
            "system_name": "",
            "cert_number": "",
            "deadline": "",
            "level": "",
        }
