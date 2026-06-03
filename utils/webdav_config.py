"""
WebDAV 配置管理模块 - 读取和保存 WebDAV 远程备份连接参数

本模块管理 WebDAV 服务器的连接配置，支持以下参数的读写：
  - 服务器地址（URL）
  - 登录认证信息（用户名/密码）
  - 远程备份路径
  - 自动备份开关

配置文件独立存储于 data/webdav_config.json，与主数据文件（dap_data.json）分离。
这样设计的好处：
  - 配置文件可以单独备份和迁移
  - 主数据文件更新不会影响 WebDAV 连接信息
  - 敏感信息（密码）可以单独管理

安全注意事项：
  - 密码以明文存储在 JSON 文件中，建议仅在可信环境中使用
  - 配置文件路径位于程序数据目录下，随程序版本一起管理

依赖：
  - json：用于配置文件的 JSON 序列化/反序列化
  - os：用于文件路径操作和目录创建
  - utils.config.Config：提供数据根目录路径
"""

# =============================================================================
# 导入区
# =============================================================================

import json  # JSON 序列化模块，用于配置文件的读写操作
import os  # 操作系统接口模块，用于路径拼接和文件存在性检查
from utils.config import Config  # 全局配置类，提供 get_data_dir() 方法获取数据目录


class WebDAVConfig:
    """WebDAV 连接配置类 - 管理远程备份的连接参数

    采用"对象属性 + 类方法"的混合模式：
      - 实例属性：存储具体配置值（url、username、password 等）
      - 类方法：load() 从文件创建实例，save() 保存实例到文件
      - 静态方法：config_path() 计算配置文件路径

    Attributes:
        url (str): WebDAV 服务器完整地址，如 https://example.com/remote.php/dav/
        username (str): WebDAV 服务器登录用户名
        password (str): WebDAV 服务器登录密码（明文存储）
        remote_path (str): 远程备份文件存储路径，默认 "/dap_backup/"
        auto_backup (bool): 是否启用自动备份功能，默认 False
    """

    def __init__(self):
        """初始化 WebDAV 配置，所有字段使用默认值"""
        self.url = ""  # 服务器地址（空字符串表示未配置）
        self.username = ""  # 登录用户名（空字符串表示未配置）
        self.password = ""  # 登录密码（空字符串表示未配置）
        self.remote_path = "/dap_backup/"  # 远程备份路径（默认值：/dap_backup/）
        self.auto_backup = False  # 是否自动备份（默认关闭，需用户手动开启）

    # =============================================================================
    # 序列化/反序列化 - 对象与字典之间的转换
    # =============================================================================

    def to_dict(self) -> dict:
        """将配置对象序列化为普通字典

        用于 JSON 文件保存前的数据准备，将对象属性转换为可序列化的基本类型。

        Returns:
            dict: 包含所有配置字段的字典
        """
        return {
            "url": self.url,              # 服务器地址
            "username": self.username,    # 登录用户名
            "password": self.password,    # 登录密码
            "remote_path": self.remote_path,  # 远程备份路径
            "auto_backup": self.auto_backup,  # 自动备份开关
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WebDAVConfig":
        """从字典反序列化创建配置对象

        安全地从 JSON 解析结果构建配置实例，对缺失的键提供默认值。

        Args:
            data: 从 JSON 文件解析出的配置字典

        Returns:
            WebDAVConfig: 填充了配置数据的实例
        """
        cfg = cls()  # 创建新实例（使用默认值作为基底）
        cfg.url = data.get("url", "")  # 提取服务器地址，无则用空字符串
        cfg.username = data.get("username", "")  # 提取用户名，无则用空字符串
        cfg.password = data.get("password", "")  # 提取密码，无则用空字符串
        cfg.remote_path = data.get("remote_path", "/dap_backup/")  # 提取远程路径，无则用默认值
        cfg.auto_backup = data.get("auto_backup", False)  # 提取自动备份开关，无则用 False
        return cfg  # 返回填充好的配置实例

    # =============================================================================
    # 文件路径与持久化
    # =============================================================================

    @staticmethod
    def config_path() -> str:
        """获取 WebDAV 配置文件的完整路径

        配置文件统一存放在程序数据目录下的 data/webdav_config.json。
        与主数据文件（data/dap_data.json）位于同一目录。

        Returns:
            str: 配置文件的完整绝对路径，如 "C:/.../data/webdav_config.json"
        """
        base = Config.get_data_dir()  # 获取程序数据根目录路径
        return os.path.join(base, "data", "webdav_config.json")  # 拼接配置文件路径

    @classmethod
    def load(cls) -> "WebDAVConfig":
        """从 JSON 文件加载 WebDAV 配置

        这是获取配置的首选方式，自动处理文件不存在和解析错误的情况。

        使用流程：
          1. 计算配置文件路径
          2. 检查文件是否存在
          3. 读取并解析 JSON 内容
          4. 从字典构建配置实例
          5. 如果任一环节失败，返回默认配置（所有字段为默认值）

        Returns:
            WebDAVConfig: 从文件加载的配置实例，或使用默认值的新实例
        """
        path = cls.config_path()  # 获取配置文件路径
        if os.path.exists(path):  # 配置文件存在
            try:
                with open(path, "r", encoding="utf-8") as f:  # 以 UTF-8 编码打开文件
                    return cls.from_dict(json.load(f))  # 解析 JSON -> 字典 -> 对象
            except (json.JSONDecodeError, IOError):  # JSON 格式错误或文件读取失败
                pass  # 容错处理：忽略错误，降级到默认配置
        return cls()  # 返回使用默认值的新实例（所有字段为空/默认）

    def save(self):
        """将当前配置保存到 JSON 文件

        保存策略：
          - 如果目标目录不存在，自动递归创建
          - 以 UTF-8 编码写入，保留中文字符（ensure_ascii=False）
          - 使用 2 空格缩进，提升文件可读性

        调用时机：
          - WebDAV 备份对话框保存按钮点击时
          - 启动时应用自动备份设置后
        """
        path = self.config_path()  # 获取配置文件路径
        os.makedirs(os.path.dirname(path), exist_ok=True)  # 递归创建目录（已存在不报错）
        with open(path, "w", encoding="utf-8") as f:  # 以写入模式打开文件
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)  # 写入 JSON，保留中文，格式化缩进
