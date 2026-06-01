"""
打包脚本 - 读取程序版本号，生成带版本信息的 EXE 文件

用法：
    python build_exe.py              # 仅构建 EXE
    python build_exe.py --release    # 构建 EXE 并创建 GitHub Release
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import Config

APP_NAME = "项目进度管理系统"
VERSION = Config.APP_VERSION
# PyInstaller 版本号格式必须是 4 段数字
version_tuple = VERSION.split(".")
while len(version_tuple) < 4:
    version_tuple.append("0")
VERSION_TUPLE = ".".join(version_tuple[:4])

# ---- 生成 PyInstaller 版本信息文件 ----
version_file = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({VERSION_TUPLE.replace('.', ', ')}),
    prodvers=({VERSION_TUPLE.replace('.', ', ')}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'080404b0',
        [
          StringStruct(u'CompanyName', u'网络安全测评团队'),
          StringStruct(u'FileDescription', u'{APP_NAME}'),
          StringStruct(u'FileVersion', u'{VERSION}'),
          StringStruct(u'InternalName', u'DAPManager'),
          StringStruct(u'LegalCopyright', u'Copyright (c) 2026'),
          StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
          StringStruct(u'ProductName', u'{APP_NAME}'),
          StringStruct(u'ProductVersion', u'{VERSION}'),
        ])
    ]),
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])]),
  ]
)
"""

ver_path = os.path.join(os.path.dirname(__file__), "version_info.txt")
with open(ver_path, "w", encoding="utf-8") as f:
    f.write(version_file.strip())

print(f"版本: {VERSION}")
print(f"文件版本: {VERSION_TUPLE}")
print("开始打包...")

# 执行 PyInstaller（排除 OCR 重依赖以控制 EXE 体积）
cmd = (
    f'python -m PyInstaller --onefile --windowed'
    f' --name "{APP_NAME}"'
    f' --version-file "{ver_path}"'
    f' --distpath "./dist"'
    f' --exclude-module easyocr'
    f' --exclude-module torch'
    f' --exclude-module torchvision'
    f' --exclude-module numpy'
    f' --exclude-module scipy'
    f' --exclude-module fitz'
    f' --exclude-module PyMuPDF'
    f' --exclude-module PIL'
    f' --exclude-module Pillow'
    f' --exclude-module cv2'
    f' --exclude-module skimage'
    f' --clean'
    f' main.py'
)
os.system(cmd)

print(f"\n打包完成！输出: dist/{APP_NAME}.exe")

# 如果指定了 --release，自动链式调用 release.py
if "--release" in sys.argv:
    print("\n>>> 自动进入发布流程...")
    import subprocess
    release_script = os.path.join(os.path.dirname(__file__), "release.py")
    subprocess.run([sys.executable, release_script, "--skip-build"])
