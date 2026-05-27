"""
WebDAV 备份服务 - 将数据文件上传/下载到 WebDAV 服务器

使用标准 HTTP 协议与 WebDAV 服务器通信，支持：
- 数据备份（上传 dap_data.json）
- 数据恢复（下载备份文件）
- 备份文件列表
- 删除远端备份
"""

import os  # 操作系统接口模块，用于检查本地文件是否存在
import json  # JSON序列化模块（备用）
import base64  # Base64编码模块，用于HTTP Basic认证的凭证编码
import urllib.request  # HTTP请求模块，用于向WebDAV服务器发送标准HTTP请求
import urllib.error  # HTTP错误处理模块，用于捕获HTTP和URL异常
from datetime import datetime, timezone, timedelta  # 日期时间模块，用于时间戳和时区转换
from email.utils import parsedate_to_datetime  # 解析RFC 2822格式的HTTP日期头
from utils.webdav_config import WebDAVConfig  # 导入WebDAV配置类

# 中国标准时间 (UTC+8)
CST = timezone(timedelta(hours=8))


def _gmt_to_cst(gmt_str: str) -> str:
    """将 GMT 时间字符串转换为中国时间 (UTC+8) 格式

    Args:
        gmt_str: WebDAV PROPFIND 返回的 GMT 时间字符串

    Returns:
        中国时间字符串 (YYYY-MM-DD HH:MM:SS)，解析失败返回原字符串
    """
    if not gmt_str:
        return ""
    try:
        dt = parsedate_to_datetime(gmt_str)  # 解析 RFC 2822 格式
        cst_dt = dt.astimezone(CST)  # 转换到中国时区
        return cst_dt.strftime("%Y-%m-%d %H:%M:%S")  # 格式化输出
    except (ValueError, TypeError, LookupError):
        return gmt_str  # 解析失败保留原值


class BackupService:
    """WebDAV 备份服务
    封装与WebDAV服务器的全部交互逻辑：
    - 连接测试（PROPFIND）
    - 数据备份（PUT）
    - 备份列表（PROPFIND）
    - 数据恢复（GET）
    - 删除备份（DELETE）
    """

    def __init__(self, config: WebDAVConfig):
        """初始化备份服务

        Args:
            config: WebDAV连接配置对象，包含服务器地址、认证信息等
        """
        self._cfg = config  # 保存配置引用，后续所有请求都使用此配置

    def _make_request(self, method: str, path: str, data: bytes = None,
                      headers: dict = None) -> tuple[bool, str, bytes]:
        """执行 WebDAV HTTP 请求（核心底层方法）
        所有与服务器的通信都通过此方法完成

        Args:
            method: HTTP方法（如：PROPFIND, GET, PUT, DELETE, MKCOL）
            path: 请求的相对路径（相对于配置中的服务器地址）
            data: 请求体数据（PUT方法时使用）
            headers: 额外的HTTP请求头

        Returns:
            (是否成功, 消息, 响应体字节数据)
        """
        # 拼接完整URL：移除配置URL末尾的斜杠，添加请求路径，移除以避免双斜杠
        url = self._cfg.url.rstrip("/") + "/" + path.lstrip("/")
        req = urllib.request.Request(url, data=data, method=method)  # 创建HTTP请求对象

        # 如果配置了用户名，则添加 HTTP Basic 认证头
        if self._cfg.username:
            creds = f"{self._cfg.username}:{self._cfg.password}"  # 拼接用户名:密码
            encoded = base64.b64encode(creds.encode("utf-8")).decode("ascii")  # Base64编码
            req.add_header("Authorization", f"Basic {encoded}")  # 添加Basic认证头

        if headers:  # 如果传入了额外的请求头
            for k, v in headers.items():  # 遍历并添加每个自定义请求头
                req.add_header(k, v)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # 发送请求，设置30秒超时
                body = resp.read()  # 读取响应体
                return True, "OK", body  # 成功返回
        except urllib.error.HTTPError as e:  # 服务器返回了HTTP错误（4xx, 5xx）
            body = e.read() if e.fp else b""  # 尝试读取错误响应体
            return False, f"HTTP {e.code}: {e.reason}", body  # 返回错误码和原因
        except urllib.error.URLError as e:  # 网络连接错误（DNS解析失败、连接超时等）
            return False, f"连接失败: {e.reason}", b""  # 返回连接失败信息
        except Exception as e:  # 其他未预期的异常
            return False, str(e), b""  # 返回异常信息

    def test_connection(self) -> tuple[bool, str]:
        """测试 WebDAV 连接是否正常
        首先尝试PROPFIND请求，如果目录不存在则尝试创建目录（MKCOL）

        Returns:
            (是否可连接, 描述消息)
        """
        if not self._cfg.url:  # 未配置服务器地址
            return False, "请先配置 WebDAV 服务器地址"

        ok, msg, _ = self._make_request("PROPFIND", self._cfg.remote_path,
                                         headers={"Depth": "0"})  # 用PROPFIND探测目录是否存在
        if ok:  # PROPFIND成功，目录存在且有权限
            return True, "连接成功"

        # 401/403 认证失败，不再尝试MKCOL
        if "401" in msg:
            return False, "认证失败：用户名或密码错误"
        if "403" in msg:
            return False, "权限不足：服务器拒绝访问"
        if "404" in msg:
            # 目录不存在，尝试创建
            ok2, msg2, _ = self._make_request("MKCOL", self._cfg.remote_path)
            if ok2 or "405" in msg2 or "409" in msg2:
                return True, "连接成功（目录已创建）"
            if "401" in msg2:
                return False, "认证失败：用户名或密码错误"
            return False, f"创建目录失败: {msg2}"
        # 其他错误
        if "DNS" in msg or "getaddrinfo" in msg or "Name or service" in msg:
            return False, "无法解析服务器地址，请检查URL是否正确"
        if "Connection refused" in msg or "Connection reset" in msg:
            return False, "服务器拒绝连接，请检查地址和端口"
        if "timeout" in msg.lower():
            return False, "连接超时，请检查网络和服务器状态"
        return False, msg  # 返回原始错误信息

    def backup(self, data_file_path: str) -> tuple[bool, str]:
        """将本地数据文件上传到 WebDAV 服务器

        Args:
            data_file_path: 本地JSON数据文件的完整路径

        Returns:
            (是否成功, 描述消息)
        """
        if not os.path.exists(data_file_path):  # 本地数据文件不存在
            return False, "数据文件不存在，请先创建项目"

        if not self._cfg.url:  # 未配置WebDAV服务器
            return False, "请先配置 WebDAV 服务器地址"

        with open(data_file_path, "rb") as f:  # 以二进制模式读取数据文件
            file_data = f.read()  # 读取文件的全部字节内容

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")  # 生成时间戳字符串（年月日_时分秒）
        remote_file = self._cfg.remote_path.rstrip("/") + f"/dap_backup_{ts}.json"  # 拼接远端文件名
        ok, msg, _ = self._make_request("PUT", remote_file, data=file_data)  # 用PUT方法上传文件

        if ok:  # 上传成功
            return True, f"备份成功: dap_backup_{ts}.json"  # 返回成功消息和文件名
        return False, msg  # 上传失败，返回错误信息

    def list_backups(self) -> tuple[bool, str, list[dict]]:
        """列出远端所有备份文件
        通过 PROPFIND 方法获取目录下的JSON文件列表及其元数据

        Returns:
            (是否成功, 消息, 备份文件信息列表)
            每个文件信息包含: name（文件名）, path（完整路径）, size（大小）, modified（修改时间）
        """
        if not self._cfg.url:  # 未配置服务器
            return False, "请先配置 WebDAV 服务器地址", []

        ok, msg, body = self._make_request(  # 发送PROPFIND请求
            "PROPFIND", self._cfg.remote_path,
            headers={"Depth": "1"},  # Depth=1表示获取目录下的直接子项
        )
        if not ok:  # 请求失败
            return False, msg, []

        files = []  # 存储解析出的文件信息
        try:
            import xml.etree.ElementTree as ET  # 导入XML解析库（用于解析PROPFIND的XML响应）
            ns = {"d": "DAV:"}  # WebDAV的XML命名空间
            root = ET.fromstring(body)  # 解析响应XML
            for resp in root.findall("d:response", ns):  # 遍历每个响应条目
                href = resp.find("d:href", ns)  # 查找文件路径元素
                if href is None:  # 没有href，跳过
                    continue
                href_text = href.text or ""  # 获取路径文本
                if not href_text.endswith(".json"):  # 过滤非JSON文件
                    continue
                props = resp.find("d:propstat/d:prop", ns)  # 查找属性集合
                size = "?"  # 默认大小（未知）
                modified = ""  # 默认修改时间（未知）
                if props is not None:  # 属性存在
                    cl = props.find("d:getcontentlength", ns)  # 获取文件大小
                    if cl is not None and cl.text:  # 大小信息存在
                        size = cl.text  # 提取大小
                    lm = props.find("d:getlastmodified", ns)  # 获取最后修改时间
                    if lm is not None and lm.text:  # 时间信息存在
                        modified = _gmt_to_cst(lm.text)  # 提取并转换为中国时区
                fname = href_text.rstrip("/").split("/")[-1]  # 从路径末尾提取文件名
                # 使用相对路径（remote_path + filename），避免 PROPFIND 绝对路径与 URL 拼接时重复
                rel_path = self._cfg.remote_path.rstrip("/") + "/" + fname
                files.append({  # 将解析结果加入列表
                    "name": fname,        # 文件名
                    "path": rel_path,     # 相对路径（用于PUT/DELETE/GET操作）
                    "size": size,         # 文件大小
                    "modified": modified, # 修改时间
                })
        except ET.ParseError:  # XML解析失败
            pass  # 忽略解析错误，返回已解析的数据（可能为空）

        return True, "OK", files  # 返回成功和文件列表

    def restore(self, remote_path: str) -> tuple[bool, str, bytes]:
        """下载指定备份文件内容（用于数据恢复）

        Args:
            remote_path: 远端备份文件的相对路径

        Returns:
            (是否成功, 消息, 文件内容字节数据)
        """
        # 确保路径以 / 开头但不含重复前缀
        path = "/" + remote_path.lstrip("/")
        ok, msg, body = self._make_request("GET", path)
        return ok, msg, body

    def delete_backup(self, remote_path: str) -> tuple[bool, str]:
        """删除远端备份文件

        Args:
            remote_path: 要删除的远端文件相对路径

        Returns:
            (是否成功, 消息)
        """
        path = "/" + remote_path.lstrip("/")
        return self._make_request("DELETE", path)
