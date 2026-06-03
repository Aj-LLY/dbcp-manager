"""
备案证 OCR 识别服务模块 - 上传备案证 PDF/图片，自动提取关键字段。

本模块提供 CertOCRService 类，用于自动识别《网络安全等级保护备案证明》
中的关键信息，减少用户手动输入。支持以下文件格式：
- PDF 格式（通过 PyMuPDF/fitz 库渲染为图片后识别）
- 常见图片格式（PNG、JPG/JPEG、BMP 等）

可识别的字段：
- company_name: 备案单位名称（公司名称）
- system_name: 被测评系统名称
- cert_number: 证书编号（格式：11位数字-5位数字）
- issue_date: 证书下发时间（输出格式：YYYY-MM-DD）
- level: 系统保护等级（归一化为：第X级）

技术栈：
- easyocr: 中文/英文 OCR 文字识别引擎（可选依赖）
- PyMuPDF (fitz): PDF 文件渲染引擎（可选依赖，仅 PDF 文件需要）
- 使用正则表达式从 OCR 结果中提取结构化字段

设计要点：
- 单例模式：easyocr.Reader 初始化耗时较长（加载模型），使用单例复用。
- 延迟初始化：首次调用 recognize() 时才加载 easyocr 模型（lazy init），
  避免程序启动时的长时间等待。
- 可选依赖：easyocr 和 PyMuPDF 均为可选依赖，未安装时给出安装提示。
- 降级策略：识别过程出现任何异常都返回空字段，不影响主流程。
"""

# ---------------------------------------------------------------------------
# 标准库导入
# ---------------------------------------------------------------------------
import os                                       # 操作系统接口，用于文件存在性检查和扩展名提取
import re                                       # 正则表达式模块，用于从 OCR 文本中提取结构化字段
import tempfile                                 # 临时文件模块（备用，部分实现可能需要临时存储截图）
from typing import Optional                     # 类型提示，用于标记可选类型（单例缓存）

# ---------------------------------------------------------------------------
# 可选第三方依赖（延迟导入，避免启动时 ImportError）
# ---------------------------------------------------------------------------
# easyocr: 用于执行 OCR 文字识别（从图片中提取中文/英文文本）
#   安装方式: pip install easyocr
#   Reader(["ch_sim", "en"], gpu=False) 创建识别器，ch_sim = 简体中文
#
# fitz (PyMuPDF): 用于将 PDF 页面渲染为高分辨率图片
#   安装方式: pip install PyMuPDF
#   fitz.open(path) 打开 PDF，page.get_pixmap(dpi=300) 渲染为图片


class CertOCRService:
    """备案证 OCR 识别服务（单例模式）。

    使用 easyocr 进行中文 OCR 文字识别，PyMuPDF 处理 PDF 文件。
    识别流程：文件路径 -> 图片字节 -> OCR 文本列表 -> 结构化字段提取。

    属性说明:
        _instance (CertOCRService | None): 类级别单例缓存。
        _initialized (bool): 是否已完成 __init__ 初始化。
        _reader (easyocr.Reader | None): easyocr 识别器实例（延迟创建）。
    """

    # 类级别单例实例缓存
    _instance: Optional["CertOCRService"] = None

    def __new__(cls):
        """单例模式 __new__ 方法。

        确保全局只有一个 CertOCRService 实例，避免重复加载
        重量级的 easyocr 模型（模型加载耗时数秒至数十秒）。

        Returns:
            CertOCRService: 全局唯一的服务实例。
        """
        if cls._instance is None:
            # 首次调用：创建新实例
            cls._instance = super().__new__(cls)
            # 标记实例尚未完成初始化
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化 OCR 服务。

        由于单例模式，__init__ 可能被多次调用。通过 _initialized 标志
        防止重复初始化。Reader 采用延迟初始化策略，首次调用 recognize()
        时才实际加载模型。
        """
        if self._initialized:
            # 已初始化：跳过重复初始化
            return
        self._initialized = True     # 标记初始化完成
        self._reader = None          # easyocr.Reader 实例延迟创建（lazy init）

    # ========================================================================
    # 延迟初始化（Lazy Init）
    # ========================================================================

    def _get_reader(self):
        """获取或创建 easyocr Reader 实例（延迟初始化）。

        easyocr 和 PyTorch 为可选依赖，仅在首次实际使用时才尝试导入。
        在 EXE 打包版本中可能未包含这些依赖，此时给出明确的安装提示。

        Reader 配置说明：
        - ["ch_sim", "en"]: 识别简体中文和英文。
        - gpu=False: 使用 CPU 模式（兼容性最好，EXE 打包后的 GPU 驱动不可用）。

        Returns:
            easyocr.Reader: 初始化完成的 OCR 识别器实例。

        Raises:
            RuntimeError: easyocr 未安装时抛出，附安装命令提示。
        """
        if self._reader is None:
            # 首次使用：尝试导入并初始化 easyocr
            try:
                # 延迟导入 easyocr（可选依赖，不在全局导入）
                import easyocr
                # 创建识别器：简体中文 + 英文，使用 CPU 模式
                self._reader = easyocr.Reader(["ch_sim", "en"], gpu=False)
            except ImportError:
                # easyocr 未安装：抛出友好的错误提示
                raise RuntimeError(
                    "OCR 识别功能需要安装 easyocr 和 PyTorch。\n"
                    "请执行: pip install easyocr PyMuPDF"
                )
        return self._reader

    # ========================================================================
    # 公共服务接口
    # ========================================================================

    def recognize(self, file_path: str) -> dict:
        """识别备案证文件，提取所有关键字段。

        完整的识别流程：
        1. 检查文件是否存在。
        2. 将文件转为图片字节数据（PDF 渲染 / 图片直接读取）。
        3. 对图片执行 OCR 文字识别。
        4. 从 OCR 文本列表中提取结构化字段。

        Args:
            file_path: PDF 或图片文件的本地完整路径。

        Returns:
            dict: 识别结果字典，包含以下键：
                - company_name (str): 备案单位名称
                - system_name (str): 系统名称
                - cert_number (str): 证书编号
                - issue_date (str): 颁发日期（YYYY-MM-DD）
                - level (str): 保护等级（如"第二级"）
                识别失败时各字段为空字符串。
        """
        # 前置校验：文件必须存在
        if not os.path.exists(file_path):
            return self._empty_result()

        try:
            # 步骤1: 将文件转为图片字节（PDF 渲染或图片直接读取）
            img_bytes = self._file_to_image(file_path)

            # 步骤2: 对图片执行 OCR 识别，获取文本列表
            texts = self._ocr_texts(img_bytes)

            # 步骤3: 从文本列表中提取结构化字段
            return self._extract_fields(texts)

        except Exception:
            # 识别过程中任何异常都返回空结果
            # 原因：OCR 识别是辅助功能，失败时不能让整个流程崩溃
            return self._empty_result()

    # ========================================================================
    # 文件预处理
    # ========================================================================

    def _file_to_image(self, file_path: str) -> bytes:
        """将 PDF 或图片文件转换为 PNG 图片的字节数据。

        处理逻辑：
        - PDF 文件：使用 PyMuPDF 打开并渲染第一页为 300 DPI 的 PNG 图片。
          高 DPI 值有助于提高 OCR 识别精度。
        - 图片文件：直接读取文件的原始字节（easyocr 支持多种图片格式）。

        Args:
            file_path: 源文件的完整路径。

        Returns:
            bytes: PNG 图片的字节数据。

        Raises:
            RuntimeError: PDF 文件但 PyMuPDF 未安装时抛出。
        """
        # 提取文件扩展名（小写），用于判断文件类型
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            # PDF 文件：需要用 PyMuPDF 渲染为图片
            try:
                # 延迟导入 fitz（PyMuPDF），它是可选依赖
                import fitz
            except ImportError:
                raise RuntimeError(
                    "PDF 文件识别需要安装 PyMuPDF。\n"
                    "请执行: pip install PyMuPDF\n"
                    "或使用 PNG/JPG 图片格式。"
                )

            # 打开 PDF 文档
            doc = fitz.open(file_path)
            # 获取第一页（等保备案证通常是单页或第一页包含关键信息）
            page = doc[0]
            # 渲染为图片：300 DPI 提供足够的清晰度用于 OCR
            pix = page.get_pixmap(dpi=300)
            # 导出为 PNG 格式的字节数据
            img_bytes = pix.tobytes("png")
            # 关闭文档释放资源
            doc.close()
            return img_bytes

        else:
            # 图片文件：直接读取原始字节
            # easyocr 的 readtext() 方法支持直接传入文件路径或字节数据
            with open(file_path, "rb") as f:
                return f.read()

    # ========================================================================
    # OCR 文字识别
    # ========================================================================

    def _ocr_texts(self, img_bytes: bytes) -> list[str]:
        """对图片字节数据执行 OCR 识别，返回识别到的文本行列表。

        使用 easyocr.Reader.readtext() 执行识别，结果中每个元素为
        (边界框, 文本, 置信度) 的元组。置信度阈值设为 0.2，低于此值的
        结果被过滤（避免噪点被误识别为文字）。

        Args:
            img_bytes: 图片的字节数据（PNG/JPG 等格式）。

        Returns:
            list[str]: 识别出的文本行列表，按图片中的位置自上而下排列。
        """
        # 获取 easyocr Reader 实例（延迟初始化）
        reader = self._get_reader()

        # 执行 OCR 识别
        results = reader.readtext(img_bytes)

        # 提取文本：只保留置信度 > 0.2 的结果
        # 为什么用 0.2 而非默认值：备案证识别场景中，某些关键文字可能因
        # 扫描质量问题导致置信度偏低，阈值过低会漏掉有效信息，阈值过高
        # 会引入噪点 —— 0.2 是在备案证场景下调试的平衡值
        return [text for _, text, conf in results if conf > 0.2]

    # ========================================================================
    # 结构化字段提取
    # ========================================================================

    def _extract_fields(self, texts: list[str]) -> dict:
        """从 OCR 文本列表中提取所有结构化字段。

        统一调用各字段的专用提取方法，返回完整的识别结果字典。

        Args:
            texts: OCR 识别的文本行列表。

        Returns:
            dict: 包含所有识别字段的字典。
        """
        # 将文本行合并为完整文本，供需要全文搜索的提取方法使用
        full_text = "\n".join(texts)

        return {
            "company_name": self._extract_company(texts),      # 提取公司名称
            "system_name": self._extract_system_name(texts),   # 提取系统名称
            "cert_number": self._extract_cert_number(full_text), # 提取证书编号
            "issue_date": self._extract_date(full_text),       # 提取颁发日期
            "level": self._extract_level(full_text),           # 提取保护等级
        }

    # -----------------------------------------------------------------------
    # 提取方法：证书编号
    # -----------------------------------------------------------------------

    def _extract_cert_number(self, text: str) -> str:
        """从全文中提取证书编号（格式：11位数字-5位数字）。

        等保备案证书的编号格式为：33000000000-24001 类似的模式。

        Args:
            text: 完整的 OCR 识别文本。

        Returns:
            str: 匹配到的证书编号，未找到时返回空字符串。
        """
        # 正则匹配：连续 11 位数字 + 短横线 + 连续 5 位数字
        m = re.search(r"\d{11}-\d{5}", text)
        return m.group(0) if m else ""

    # -----------------------------------------------------------------------
    # 提取方法：公司名称（备案单位）
    # -----------------------------------------------------------------------

    def _extract_company(self, texts: list[str]) -> str:
        """从 OCR 文本行列表中提取公司名称。

        提取策略（按优先级）：
        1. 找到包含"单位"关键词的行，取其前一行（如果前一行是纯中文文本）。
           （备案证上"备案单位"关键字的上一行即为公司名称）
        2. 找包含"的:"的行，取冒号前的部分（如果以"公司"结尾）。
           （如"备案单位的:XXX公司"）

        Args:
            texts: OCR 识别的文本行列表。

        Returns:
            str: 提取到的公司名称，未找到时返回空字符串。
        """
        for i, t in enumerate(texts):
            t_clean = t.strip()

            # 策略1: 找到"单位"关键词，取前一行
            if "单位" in t_clean and i > 0:
                prev = texts[i - 1].strip()
                # 前一行必须是 2-30 个纯中文字符（含括号）
                # 这确保了前一行确实是机构名，而不是其他无关文字
                if re.match(r"^[\u4e00-\u9fa5()（）]{2,30}$", prev):
                    return prev

            # 策略2: "的:" 分割模式
            if "的:" in t_clean:
                before = t_clean.split("的:")[0]
                if re.search(r"公司$", before):
                    return before

        # 所有策略都未匹配到
        return ""

    # -----------------------------------------------------------------------
    # 提取方法：系统名称
    # -----------------------------------------------------------------------

    def _extract_system_name(self, texts: list[str]) -> str:
        """从 OCR 文本行列表中提取系统名称。

        提取策略（按优先级）：
        1. 找到包含"系统"的行，且"系统"前有足够文字，取"系统"前的部分。
        2. 如果"系统"在行首位置，取其上一行的文字（综合评估场景）。

        Args:
            texts: OCR 识别的文本行列表。

        Returns:
            str: 提取到的系统名称，未找到时返回空字符串。
        """
        for i, t in enumerate(texts):
            t_clean = t.strip()

            if "系统" in t_clean:
                idx = t_clean.find("系统")
                if idx > 0:
                    # "系统"前面有文字：提取前面的部分作为系统名
                    name = t_clean[:idx]
                    # 去除末尾的标点符号（如句号、逗号等）
                    name = re.sub(r"[.。一,，]$", "", name).strip()
                    if len(name) >= 2:
                        # 系统名至少 2 个字符才合理
                        return name

                if idx <= 1 and i > 0:
                    # "系统"在行首或第2个字符位置：可能前一行是系统名
                    prev = texts[i - 1].strip()
                    if len(prev) >= 2 and not re.match(r"^[第一二三四五\d]", prev):
                        # 前一行不是"第X条"之类的条款编号
                        return prev

        # 所有策略都未匹配到
        return ""

    # -----------------------------------------------------------------------
    # 提取方法：保护等级
    # -----------------------------------------------------------------------

    def _extract_level(self, text: str) -> str:
        """从全文中提取系统保护等级，统一归一化为"第X级"格式。

        支持识别格式：
        - 中文数字：第一级、第二级、...、第五级
        - 阿拉伯数字：第1级、第2级、...、第5级
        - 带空格的变体：第 二 级

        结果统一归一化为"第X级"（中文数字）。

        Args:
            text: 完整的 OCR 识别文本。

        Returns:
            str: 归一化后的等级字符串，如"第二级"，未找到返回空字符串。
        """
        # 阿拉伯数字到中文数字的映射表
        num_map = {"1": "一", "2": "二", "3": "三", "4": "四", "5": "五"}

        # 正则匹配：可选"第" + 可选空白 + 数字（中文或阿拉伯） + 可选空白 + "级"
        m = re.search(r"第?\s*([一二三四五1-5])\s*级", text)
        if m:
            d = m.group(1)
            # 阿拉伯数字转为中文数字，中文数字保持不变
            num = num_map.get(d, d)
            return f"第{num}级"

        # 未找到等级标识
        return ""

    # -----------------------------------------------------------------------
    # 提取方法：颁发日期
    # -----------------------------------------------------------------------

    def _extract_date(self, text: str) -> str:
        """从全文中提取证书颁发日期，统一转换为 YYYY-MM-DD 格式。

        支持的日期格式：
        1. 中文日期：2024年1月15日 -> 2024-01-15（主要格式）
        2. 数字日期：2024-01-15 或 2024/01/15 -> 2024-01-15（备用格式）

        Args:
            text: 完整的 OCR 识别文本。

        Returns:
            str: YYYY-MM-DD 格式的日期字符串（月份和日期补零到两位），
                 未找到时返回空字符串。
        """
        # 策略1: 匹配中文日期格式 "YYYY年MM月DD日"
        m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
        if m:
            y, mo, d = m.groups()
            # 补零：将 "1" 格式化为 "01"
            return f"{y}-{int(mo):02d}-{int(d):02d}"

        # 策略2: 匹配数字日期格式 "YYYY-MM-DD" 或 "YYYY/MM/DD"
        m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
        if m:
            y, mo, d = m.groups()
            return f"{y}-{int(mo):02d}-{int(d):02d}"

        # 所有格式都未匹配到
        return ""

    # ========================================================================
    # 空结果返回
    # ========================================================================

    def _empty_result(self) -> dict:
        """返回全部字段为空字符串的识别结果。

        在以下情况使用：
        - 文件不存在
        - OCR 识别过程出现异常
        - 无法从文件中识别出任何有效字段

        Returns:
            dict: 所有字段值为空字符串的字典。
        """
        return {
            "company_name": "",
            "system_name": "",
            "cert_number": "",
            "issue_date": "",
            "level": "",
        }
