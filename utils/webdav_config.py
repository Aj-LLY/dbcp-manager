"""
WebDAV 配置管理 - 读取和保存 WebDAV 连接参数

配置文件存储于 data/webdav_config.json，与主数据文件独立
"""

import json  # JSON序列化模块，用于配置文件的读写
import os  # 操作系统接口模块，用于路径拼接和文件检查
from utils.config import Config  # 导入配置类，用于获取数据目录路径


class WebDAVConfig:
    """WebDAV 连接配置
    管理WebDAV服务器的连接参数：地址、认证信息、远程路径和自动备份开关
    支持从JSON文件加载和保存配置
    """

    def __init__(self):
        """初始化WebDAV配置，设置默认值"""
        self.url = ""  # WebDAV服务器地址（如 https://example.com/remote.php/dav/）
        self.username = ""  # WebDAV服务器的登录用户名
        self.password = ""  # WebDAV服务器的登录密码
        self.remote_path = "/dap_backup/"  # 远程备份文件的存储路径（默认 /dap_backup/）
        self.auto_backup = False  # 是否启用自动备份功能

    def to_dict(self) -> dict:
        """将配置对象序列化为字典，用于JSON保存"""
        return {
            "url": self.url,              # 服务器地址
            "username": self.username,    # 用户名
            "password": self.password,    # 密码
            "remote_path": self.remote_path,  # 远程路径
            "auto_backup": self.auto_backup,  # 自动备份开关
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WebDAVConfig":
        """从字典反序列化创建配置对象

        Args:
            data: 包含配置信息的字典

        Returns:
            填充了配置数据的 WebDAVConfig 实例
        """
        cfg = cls()  # 创建新实例（使用默认值）
        cfg.url = data.get("url", "")  # 从字典中提取服务器地址，不存在则为空字符串
        cfg.username = data.get("username", "")  # 从字典中提取用户名
        cfg.password = data.get("password", "")  # 从字典中提取密码
        cfg.remote_path = data.get("remote_path", "/dap_backup/")  # 从字典中提取远程路径，默认 /dap_backup/
        cfg.auto_backup = data.get("auto_backup", False)  # 从字典中提取自动备份开关，默认关闭
        return cfg  # 返回配置好的实例

    @staticmethod
    def config_path() -> str:
        """获取WebDAV配置文件的完整路径
        配置文件统一存放在 data/webdav_config.json
        """
        base = Config.get_data_dir()  # 获取程序数据目录路径
        return os.path.join(base, "data", "webdav_config.json")  # 拼接配置文件完整路径

    @classmethod
    def load(cls) -> "WebDAVConfig":
        """从文件加载WebDAV配置
        如果配置文件不存在或解析失败，则返回默认配置（所有字段为空）
        """
        path = cls.config_path()  # 获取配置文件路径
        if os.path.exists(path):  # 检查配置文件是否存在
            try:
                with open(path, "r", encoding="utf-8") as f:  # 以UTF-8编码读取配置文件
                    return cls.from_dict(json.load(f))  # 解析JSON并创建配置对象
            except (json.JSONDecodeError, IOError):  # JSON解析错误或文件读取失败
                pass  # 容错处理：忽略错误，继续返回默认配置
        return cls()  # 返回使用默认值的配置对象

    def save(self):
        """将当前配置保存到文件
        如果目标目录不存在则自动创建
        """
        path = self.config_path()  # 获取配置文件路径
        os.makedirs(os.path.dirname(path), exist_ok=True)  # 确保配置文件所在目录存在
        with open(path, "w", encoding="utf-8") as f:  # 以写入模式打开文件
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)  # 写入JSON，保留中文，格式化缩进
