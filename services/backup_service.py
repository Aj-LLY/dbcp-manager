"""
WebDAV 备份服务模块 - 将等保测评项目数据备份到远程 WebDAV 服务器。

本模块使用标准 HTTP 协议与 WebDAV 服务器通信，支持以下功能：
1. 连接测试（PROPFIND）：验证服务器地址、认证信息和目录是否存在。
2. 数据备份（PUT）：将本地 dap_data.json 文件上传到服务器的指定目录。
3. 备份列表（PROPFIND）：获取服务器上所有备份文件及其元数据。
4. 数据恢复（GET）：从服务器下载指定备份文件到本地。
5. 删除备份（DELETE）：从服务器删除不再需要的备份文件。

技术实现要点：
- 使用 urllib.request（Python 标准库）发送 HTTP 请求，无需额外依赖。
- 支持 HTTP Basic 认证（用户名:密码经过 Base64 编码）。
- 自动将 GMT 时间转换为中国标准时间（UTC+8）用于显示。
- 备份文件命名规则：dap_backup_YYYYMMDD_HHMMSS.json

依赖关系：
- WebDAVConfig: 配置文件类，包含服务器地址、认证信息、远程路径等。
"""

# ---------------------------------------------------------------------------
# 标准库导入
# ---------------------------------------------------------------------------
import base64                                               # Base64 编解码，用于 HTTP Basic 认证的凭证编码
import json                                                 # JSON 序列化模块（备用）
import os                                                   # 操作系统接口，用于检查本地文件是否存在
import urllib.error                                         # HTTP 错误处理，捕获 4xx/5xx 等服务器级错误
import urllib.request                                       # HTTP 请求发送，支持 GET/PUT/DELETE/PROPFIND/MKCOL 等方法
from datetime import datetime, timedelta, timezone           # 日期时间处理，用于时区转换和时间戳生成
from email.utils import parsedate_to_datetime               # 解析 RFC 2822 格式的 HTTP 日期头（GMT 时间）

# ---------------------------------------------------------------------------
# 项目内导入（配置层）
# ---------------------------------------------------------------------------
from utils.webdav_config import WebDAVConfig
# WebDAVConfig: WebDAV 连接配置类，包含 url, username, password, remote_path 等属性

# ===========================================================================
# 模块级常量
# ===========================================================================

# 中国标准时间（UTC+8）时区对象
CST = timezone(timedelta(hours=8))


# ===========================================================================
# 模块级工具函数
# ===========================================================================

def _gmt_to_cst(gmt_str: str) -> str:
    """将 GMT 时间字符串转换为中国标准时间（UTC+8）格式。

    WebDAV 的 PROPFIND 响应中，文件的最后修改时间使用 RFC 2822 格式的
    GMT 时间字符串（如 "Mon, 01 Jan 2024 12:00:00 GMT"），本函数将其转换
    为本地可读的中国时间格式。

    Args:
        gmt_str: RFC 2822 格式的 GMT 时间字符串。

    Returns:
        str: 转换后的中国时间字符串（YYYY-MM-DD HH:MM:SS 格式），
             解析失败时返回空字符串或原字符串。
    """
    if not gmt_str:
        # 空字符串直接返回空，避免 parse 抛出异常
        return ""
    try:
        # 使用标准库的 parsedate_to_datetime 解析 RFC 2822 格式
        dt = parsedate_to_datetime(gmt_str)
        # 转换到中国时区（UTC+8）
        cst_dt = dt.astimezone(CST)
        # 格式化为人类可读的字符串
        return cst_dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, LookupError):
        # 解析失败（格式异常、空对象等）：返回原字符串作为降级方案
        return gmt_str


# ===========================================================================
# BackupService 类
# ===========================================================================

class BackupService:
    """WebDAV 备份服务。

    封装与远程 WebDAV 服务器的全部通信逻辑，提供高层次的备份/恢复操作接口。
    所有 HTTP 请求通过 _make_request() 核心方法发出，统一处理认证、超时和错误。

    支持的 WebDAV 方法:
    - PROPFIND: 获取远程目录属性 / 列出文件列表
    - PUT: 上传备份文件到远程服务器
    - GET: 从远程服务器下载备份文件（恢复）
    - DELETE: 删除远程服务器上的备份文件
    - MKCOL: 创建远程目录（首次连接测试时自动创建）

    认证方式:
        HTTP Basic 认证（用户名:密码 Base64 编码），通过 Authorization 头传递。

    超时设置:
        所有 HTTP 请求统一设置为 30 秒超时。

    备份文件命名规则:
        dap_backup_YYYYMMDD_HHMMSS.json（时间戳采用本地时间）。

    属性说明:
        _cfg (WebDAVConfig): WebDAV 连接配置对象，包含服务器地址和认证凭据。
    """

    def __init__(self, config: WebDAVConfig):
        """初始化备份服务。

        Args:
            config: WebDAV 连接的完整配置对象，包含：
                    - url: 服务器地址（如 https://webdav.example.com/remote.php/dav/）
                    - username: 认证用户名
                    - password: 认证密码
                    - remote_path: 远程存储目录路径
        """
        # 保存配置引用，后续所有 HTTP 请求都使用此配置
        self._cfg = config

    # ========================================================================
    # 核心 HTTP 请求方法
    # ========================================================================

    def _make_request(self, method: str, path: str, data: bytes = None,
                      headers: dict = None) -> tuple[bool, str, bytes]:
        """执行 WebDAV HTTP 请求（核心底层方法）。

        所有与 WebDAV 服务器的通信都通过此方法完成，提供统一的：
        - URL 拼接逻辑（配置 URL + 请求路径）。
        - HTTP Basic 认证处理（自动编码用户名和密码）。
        - 超时控制（30 秒）。
        - 错误分类处理（HTTP 错误、连接错误、其他异常）。

        Args:
            method: HTTP 请求方法（如：GET, PUT, DELETE, PROPFIND, MKCOL）。
            path: 请求的相对路径（相对于配置中的服务器根URL）。
            data: 请求体数据（仅 PUT 等方法需要，GET/DELETE 等为 None）。
            headers: 额外的 HTTP 请求头字典。

        Returns:
            tuple[bool, str, bytes]:
                - bool: 请求是否成功（HTTP 200 级别）。
                - str: 成功时为 "OK"，失败时为错误描述信息。
                - bytes: 成功时为响应体字节数据，失败时为错误信息或空字节。
        """
        # 拼接完整 URL：移除配置 URL 末尾的斜杠，添加请求路径
        # 注意：path 可能包含前导斜杠，需要 lstrip 避免双斜杠
        url = self._cfg.url.rstrip("/") + "/" + path.lstrip("/")

        # 创建 HTTP 请求对象，指定 URL、请求方法和请求体
        req = urllib.request.Request(url, data=data, method=method)

        # 如果配置了用户名，添加 HTTP Basic 认证头
        if self._cfg.username:
            # 组装 "用户名:密码" 字符串
            creds = f"{self._cfg.username}:{self._cfg.password}"
            # Base64 编码（HTTP Basic 认证标准要求）
            encoded = base64.b64encode(creds.encode("utf-8")).decode("ascii")
            # 添加 Authorization 头
            req.add_header("Authorization", f"Basic {encoded}")

        # 添加用户指定的额外请求头（如 PROPFIND 的 Depth 头）
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        try:
            # 发送 HTTP 请求，设置 30 秒超时
            with urllib.request.urlopen(req, timeout=30) as resp:
                # 读取完整响应体
                body = resp.read()
                return True, "OK", body

        except urllib.error.HTTPError as e:
            # 服务器返回了 4xx 或 5xx 级别的 HTTP 错误
            # 尝试读取错误响应体（可能包含更详细的错误信息）
            body = e.read() if e.fp else b""
            return False, f"HTTP {e.code}: {e.reason}", body

        except urllib.error.URLError as e:
            # 网络层面的错误：DNS 解析失败、连接超时、连接被拒绝等
            return False, f"连接失败: {e.reason}", b""

        except Exception as e:
            # 其他未预期的 Python 异常
            return False, str(e), b""

    # ========================================================================
    # 连接测试
    # ========================================================================

    def test_connection(self) -> tuple[bool, str]:
        """测试与 WebDAV 服务器的连接是否正常。

        测试逻辑：
        1. 先检查是否配置了服务器地址。
        2. 发送 PROPFIND 请求探测目标目录是否存在。
        3. 如果目录不存在（404），尝试用 MKCOL 创建目录。
        4. 服务端响应非标准 404 时不做创建尝试（如 Nutstore、InfiniCLOUD 返回 403/200 但目录仍存在）。

        Returns:
            tuple[bool, str]:
                - bool: 是否可成功连接。
                - str: 连接状态的描述信息。
        """
        # 前置校验：服务器地址不能为空
        if not self._cfg.url:
            return False, "请先配置 WebDAV 服务器地址"

        # 第一步：用 PROPFIND 探测目标目录是否存在
        # Depth: 0 表示只获取目录自身的属性，不递归子项
        ok, msg, _ = self._make_request("PROPFIND", self._cfg.remote_path,
                                        headers={"Depth": "0"})

        if ok:
            # PROPFIND 成功：目录存在且有访问权限
            return True, "连接成功"

        # PROPFIND 失败：根据错误码分类处理
        # 401 未授权：用户名或密码错误
        if "401" in msg:
            return False, "认证失败：用户名或密码错误"

        # 403 禁止访问：服务器拒绝访问请求
        if "403" in msg:
            return False, "权限不足：服务器拒绝访问"

        # 404 Not Found: 目标目录不存在，尝试用 MKCOL 自动创建
        # 这是首次连接的常见情况 —— 远程还没有备份目录
        if "404" in msg:
            # 用 MKCOL 方法尝试创建远程目录（WebDAV 创建目录的标准方法）
            ok2, msg2, _ = self._make_request("MKCOL", self._cfg.remote_path)
            if ok2 or "405" in msg2 or "409" in msg2:
                # MKCOL 成功返回 201 Created
                # 405 Method Not Allowed: 目录创建权限不足但目录可能存在
                # 409 Conflict: 目录已存在（被其他客户端创建）
                return True, "连接成功（目录已创建）"
            if "401" in msg2:
                # MKCOL 时认证失败：用户名或密码错误
                return False, "认证失败：用户名或密码错误"
            return False, f"创建目录失败: {msg2}"

        # 其他未分类错误：尝试从错误消息中识别常见网络问题并给出中文提示
        # DNS 解析失败（地址拼写错误 / 域名不存在 / 无法解析）
        if "DNS" in msg or "getaddrinfo" in msg or "Name or service" in msg:
            return False, "无法解析服务器地址，请检查URL是否正确"
        # 连接被拒绝（端口错误 / 防火墙拦截 / 服务未运行）
        if "Connection refused" in msg or "Connection reset" in msg:
            return False, "服务器拒绝连接，请检查地址和端口"
        # 连接超时（网络不可达 / 服务器响应过慢 / 被防火墙丢包）
        if "timeout" in msg.lower():
            return False, "连接超时，请检查网络和服务器状态"

        # 无法归类的错误：透传原始消息给用户
        return False, msg

    # ========================================================================
    # 数据备份（上传）
    # ========================================================================

    def backup(self, data_file_path: str) -> tuple[bool, str]:
        """将本地数据文件上传到 WebDAV 服务器进行备份。

        上传前会检查：
        1. 本地数据文件是否存在。
        2. WebDAV 服务器地址是否已配置。

        备份文件使用时间戳命名：dap_backup_YYYYMMDD_HHMMSS.json
        这种命名方式确保每次备份都有唯一的文件名，避免相互覆盖。

        Args:
            data_file_path: 本地 JSON 数据文件的完整路径（dap_data.json）。

        Returns:
            tuple[bool, str]:
                - bool: 备份是否成功。
                - str: 成功时包含文件名，失败时包含错误原因。
        """
        # 前置校验1：本地数据文件必须存在
        if not os.path.exists(data_file_path):
            return False, "数据文件不存在，请先创建项目"

        # 前置校验2：WebDAV 服务器地址必须已配置
        if not self._cfg.url:
            return False, "请先配置 WebDAV 服务器地址"

        # 以二进制模式读取本地数据文件的全部内容
        with open(data_file_path, "rb") as f:
            file_data = f.read()

        # 生成备份文件名：dap_backup_年月日_时分秒.json
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 拼接远程文件完整路径（相对于配置中的 remote_path）
        remote_file = self._cfg.remote_path.rstrip("/") + f"/dap_backup_{ts}.json"

        # 使用 PUT 方法将文件数据上传到 WebDAV 服务器
        ok, msg, _ = self._make_request("PUT", remote_file, data=file_data)

        if ok:
            # 上传成功：返回包含文件名的友好提示
            return True, f"备份成功: dap_backup_{ts}.json"
        # 上传失败：透传错误信息
        return False, msg

    # ========================================================================
    # 备份列表（查询远端文件）
    # ========================================================================

    def list_backups(self) -> tuple[bool, str, list[dict]]:
        """列出 WebDAV 服务器上远程目录中的所有备份文件。

        通过 PROPFIND 方法获取目录下的所有 JSON 文件及其元数据，
        包括文件名、大小和最后修改时间。非 JSON 文件会被自动过滤掉。

        PROPFIND Depth 参数说明：
        - Depth: 0 只返回目录本身。
        - Depth: 1 返回目录本身及其直接子项（本方法使用此值）。
        - Depth: infinity 递归返回所有后代项。

        Returns:
            tuple[bool, str, list[dict]]:
                - bool: 是否成功获取文件列表。
                - str: 描述消息。
                - list[dict]: 文件信息列表，每个元素包含：
                    - name (str): 文件名。
                    - path (str): 文件的相对路径（用于下载/删除操作）。
                    - size (str): 文件大小（字节数，未知为 "?"）。
                    - modified (str): 最后修改时间（中国时区格式）。
        """
        # 前置校验：服务器地址必须已配置
        if not self._cfg.url:
            return False, "请先配置 WebDAV 服务器地址", []

        # 发送 PROPFIND 请求获取目录内容
        # Depth: 1 表示获取目录本身及其直接子文件/子目录的属性
        ok, msg, body = self._make_request(
            "PROPFIND", self._cfg.remote_path,
            headers={"Depth": "1"},
        )

        if not ok:
            # 请求失败：返回错误信息
            return False, msg, []

        files = []  # 存储解析出的备份文件信息

        try:
            # 使用标准库 xml.etree.ElementTree 解析 PROPFIND 的 XML 响应
            # PROPFIND 响应示例结构:
            # <d:multistatus xmlns:d="DAV:">
            #   <d:response>
            #     <d:href>/remote.php/dav/files/user/dap_backup_20240101_120000.json</d:href>
            #     <d:propstat>
            #       <d:prop>
            #         <d:getcontentlength>12345</d:getcontentlength>
            #         <d:getlastmodified>Mon, 01 Jan 2024 12:00:00 GMT</d:getlastmodified>
            #       </d:prop>
            #       <d:status>HTTP/1.1 200 OK</d:status>
            #     </d:propstat>
            #   </d:response>
            # </d:multistatus>
            import xml.etree.ElementTree as ET

            # WebDAV 属性使用的 XML 命名空间
            # DAV: 是所有 WebDAV 标准属性的命名空间前缀
            ns = {"d": "DAV:"}

            # 解析 XML 响应体
            root = ET.fromstring(body)

            # 遍历每个 <d:response> 元素 —— 每个 response 对应远程目录中的一个文件或子目录
            for resp in root.findall("d:response", ns):
                # 提取文件的 href（即文件的远程相对路径）
                # 例如: /remote.php/dav/files/user/dap_backup_20240101_120000.json
                href = resp.find("d:href", ns)
                if href is None:
                    # 没有 href 的条目：跳过
                    continue

                href_text = href.text or ""

                # 只处理 JSON 文件（备份文件），忽略目录和其他类型文件
                if not href_text.endswith(".json"):
                    continue

                # 提取文件属性：内容长度和最后修改时间
                # props 位于 d:propstat/d:prop 路径下
                props = resp.find("d:propstat/d:prop", ns)
                size = "?"       # 文件大小（字节），默认为未知（"?" 显示为 ?）
                modified = ""    # 修改时间，默认为空字符串

                if props is not None:
                    # 提取文件内容长度（getcontentlength = 文件字节数）
                    cl = props.find("d:getcontentlength", ns)
                    if cl is not None and cl.text:
                        size = cl.text

                    # 提取最后修改时间（getlastmodified = RFC 2822 GMT 格式）
                    # 例如: "Mon, 01 Jan 2024 12:00:00 GMT"
                    lm = props.find("d:getlastmodified", ns)
                    if lm is not None and lm.text:
                        # 通过 _gmt_to_cst 转换为中国标准时间（UTC+8）供 UI 显示
                        modified = _gmt_to_cst(lm.text)

                # 从 href 路径末尾提取纯文件名（去掉目录前缀）
                # 例如: "/path/to/dap_backup_20240101_120000.json" -> "dap_backup_20240101_120000.json"
                fname = href_text.rstrip("/").split("/")[-1]

                # 构建相对路径（remote_path + filename），用于后续的 GET/DELETE 操作
                rel_path = self._cfg.remote_path.rstrip("/") + "/" + fname

                # 将解析结果加入文件列表
                files.append({
                    "name": fname,
                    "path": rel_path,
                    "size": size,
                    "modified": modified,
                })

        except ET.ParseError:
            # XML 解析失败（非标准响应）：忽略，返回已成功解析的部分数据
            pass

        return True, "OK", files

    # ========================================================================
    # 数据恢复（下载）
    # ========================================================================

    def restore(self, remote_path: str) -> tuple[bool, str, bytes]:
        """从 WebDAV 服务器下载指定备份文件，用于数据恢复。

        下载完成后，调用方需要将返回的字节数据写入本地的 dap_data.json 文件，
        然后调用 DataService.reload() 刷新内存中的数据。

        Args:
            remote_path: 要下载的远端备份文件的相对路径。

        Returns:
            tuple[bool, str, bytes]:
                - bool: 下载是否成功。
                - str: 描述消息。
                - bytes: 成功时为文件的完整字节内容，失败时为空字节。
        """
        # 确保路径以 "/" 开头，构建规范的请求路径
        path = "/" + remote_path.lstrip("/")
        # 使用 GET 方法下载文件
        ok, msg, body = self._make_request("GET", path)
        return ok, msg, body

    # ========================================================================
    # 删除远程备份
    # ========================================================================

    def delete_backup(self, remote_path: str) -> tuple[bool, str]:
        """从 WebDAV 服务器删除指定的备份文件。

        Args:
            remote_path: 要删除的远端备份文件的相对路径。

        Returns:
            tuple[bool, str]: (是否成功, 描述消息)。
        """
        # 确保路径以 "/" 开头，构建规范的请求路径
        path = "/" + remote_path.lstrip("/")
        # 使用 DELETE 方法删除远程文件
        ok, msg, _ = self._make_request("DELETE", path)
        return ok, msg
