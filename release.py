"""
发布脚本 - 构建 EXE、打标签、创建 GitHub Release 并上传资产

用法:
    python release.py              # 构建 + 发布（需要 gh CLI 已登录）
    python release.py --skip-build # 跳过构建，直接发布已有 EXE
    python release.py --dry-run    # 仅显示将要执行的步骤，不实际操作

依赖:
    - GitHub CLI (gh): https://cli.github.com/
    - 认证方式一: gh auth login（交互式浏览器登录）
    - 认证方式二: export GITHUB_TOKEN="ghp_xxx"（适用于无浏览器/网络受限环境）
"""

import sys
import os
import subprocess
import argparse
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.config import Config

APP_NAME = "项目进度管理系统"
VERSION = Config.APP_VERSION
EXE_NAME = f"{APP_NAME}_v{VERSION}.exe"
RELEASE_EXE_NAME = f"{APP_NAME}_v{VERSION}.exe"
# gh CLI 在 Windows 下处理中文文件名会截断字符，使用 ASCII 临时文件名
ASCII_EXE_NAME = f"dap_v{VERSION}.exe"
DIST_PATH = os.path.join(os.path.dirname(__file__), "dist", EXE_NAME)
RELEASES_DIR = os.path.join(os.path.dirname(__file__), "releases")
RELEASE_EXE_PATH = os.path.join(RELEASES_DIR, RELEASE_EXE_NAME)

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def run(cmd, cwd=None, check=True):
    """执行命令并打印"""
    print(f"{YELLOW}> {cmd}{RESET}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if check and result.returncode != 0:
        print(f"{RED}命令执行失败 (exit={result.returncode}){RESET}")
        sys.exit(1)
    return result.returncode == 0


def find_gh():
    """查找 gh CLI 路径"""
    paths = [
        os.path.expandvars(r"%ProgramFiles%\GitHub CLI\gh.exe"),
        os.path.expandvars(r"%LocalAppData%\Programs\GitHub CLI\gh.exe"),
        "gh",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
        try:
            subprocess.run(
                [p, "--version"], capture_output=True, timeout=5,
                encoding="utf-8", errors="replace",
            )
            return p
        except Exception:
            continue
    return None


def check_prerequisites(gh_path):
    """检查前置条件"""
    project_dir = os.path.dirname(os.path.abspath(__file__))

    # 检查 gh CLI
    if not gh_path:
        msg = "未找到 GitHub CLI (gh)\n请安装: https://cli.github.com/\n安装后执行: gh auth login"
        if args.dry_run:
            print(f"{YELLOW}[DRY-RUN] {msg}{RESET}")
        else:
            print(f"{RED}错误: {msg}{RESET}")
            sys.exit(1)
        return

    # 检查 gh 登录状态
    result = subprocess.run(
        [gh_path, "auth", "status"], capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        msg = "gh CLI 未登录\n请执行: gh auth login"
        if args.dry_run:
            print(f"{YELLOW}[DRY-RUN] {msg}{RESET}")
        else:
            print(f"{RED}错误: {msg}{RESET}")
            sys.exit(1)

    # 检查是否在 git 仓库中
    git_dir = os.path.join(project_dir, ".git")
    if not os.path.exists(git_dir):
        print(f"{RED}错误: 当前目录不是 git 仓库{RESET}")
        sys.exit(1)

    # 检查工作区是否干净
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True,
        cwd=project_dir, encoding="utf-8", errors="replace",
    )
    if result.stdout.strip():
        print(f"{YELLOW}警告: 工作区有未提交的更改，请先 commit 或 stash{RESET}")
        print(result.stdout)
        if not args.dry_run:
            resp = input("是否继续? [y/N] ").strip().lower()
            if resp != "y":
                sys.exit(0)


def build_exe():
    """构建 EXE"""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"\n{GREEN}=== 步骤 1: 构建 EXE ==={RESET}")
    run(f'"{sys.executable}" build_exe.py', cwd=project_dir)

    if not os.path.exists(DIST_PATH):
        print(f"{RED}错误: 构建失败，未找到 {DIST_PATH}{RESET}")
        sys.exit(1)

    # 复制到 releases 目录
    os.makedirs(RELEASES_DIR, exist_ok=True)
    import shutil
    shutil.copy2(DIST_PATH, RELEASE_EXE_PATH)
    print(f"{GREEN}已复制: {RELEASE_EXE_PATH}{RESET}")


def extract_changelog():
    """从 CHANGELOG.md 提取当前版本的发布说明"""
    changelog_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "CHANGELOG.md"
    )
    if not os.path.exists(changelog_path):
        return f"v{VERSION}"

    with open(changelog_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 查找当前版本条目
    marker = f"## v{VERSION}"
    idx = content.find(marker)
    if idx == -1:
        return f"v{VERSION}"

    # 提取到下一个 ## 标题之前的内容
    rest = content[idx + len(marker):]
    next_marker = rest.find("\n## ")
    if next_marker == -1:
        notes = rest.strip()
    else:
        notes = rest[:next_marker].strip()

    return notes if notes else f"v{VERSION}"


def create_release(gh_path):
    """创建 GitHub Release"""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    tag = f"v{VERSION}"

    print(f"\n{GREEN}=== 步骤 2: 创建 Git Tag ==={RESET}")

    # 检查 tag 是否已存在
    result = subprocess.run(
        ["git", "tag", "-l", tag], capture_output=True, text=True,
        cwd=project_dir, encoding="utf-8", errors="replace",
    )
    if result.stdout.strip():
        print(f"{YELLOW}Tag {tag} 已存在，将删除后重新创建{RESET}")
        run(f'git tag -d {tag}', cwd=project_dir)
        run(f'git push origin :refs/tags/{tag}', cwd=project_dir, check=False)

    run(f'git tag -a {tag} -m "{APP_NAME} {tag}"', cwd=project_dir)
    run(f"git push origin {tag}", cwd=project_dir)

    print(f"\n{GREEN}=== 步骤 3: 创建 GitHub Release ==={RESET}")

    # 提取 changelog 作为 release notes
    notes = extract_changelog()
    print(f"Release Notes:\n{notes}\n")

    # gh CLI 在 Windows 下处理中文文件名会截断字符
    # 方案：复制到临时 ASCII 文件名，用 filepath#displayname 语法上传
    # displayname 中的中文会被 gh 存入 asset label
    tmp_exe = os.path.join(tempfile.gettempdir(), ASCII_EXE_NAME)
    shutil.copy2(RELEASE_EXE_PATH, tmp_exe)
    # 使用 # 分隔：gh 将 # 后面的部分设为 asset label（下载时显示的名称）
    upload_arg = f"{tmp_exe}#{RELEASE_EXE_NAME}"
    print(f"{YELLOW}临时文件: {tmp_exe}{RESET}")
    print(f"{YELLOW}上传参数: {upload_arg}{RESET}")

    # 创建 release 并上传资产
    cmd = (
        f'"{gh_path}" release create {tag}'
        f' "{upload_arg}"'
        f' --title "{APP_NAME} {tag}"'
        f' --notes "{notes}"'
    )
    run(cmd, cwd=project_dir)

    # 清理临时文件
    try:
        os.remove(tmp_exe)
    except OSError:
        pass

    print(f"\n{GREEN}========================================{RESET}")
    print(f"{GREEN}发布完成!{RESET}")
    print(f"版本: {tag}")
    print(f"资产: {RELEASE_EXE_NAME}")
    print(f"查看: https://github.com/Aj-LLY/dbcp-manager/releases/tag/{tag}")


def main():
    global args
    parser = argparse.ArgumentParser(description=f"{APP_NAME} 发布脚本")
    parser.add_argument("--skip-build", action="store_true", help="跳过构建步骤")
    parser.add_argument("--dry-run", action="store_true", help="仅检查不执行")
    args = parser.parse_args()

    project_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 60)
    print(f"  {APP_NAME} 发布脚本")
    print(f"  版本: v{VERSION}")
    print(f"  EXE:  {RELEASE_EXE_NAME}")
    print("=" * 60)

    gh_path = find_gh()
    check_prerequisites(gh_path)

    if args.dry_run:
        print(f"\n{YELLOW}[DRY-RUN] 将执行以下步骤:{RESET}")
        if not args.skip_build:
            print(f"  1. 构建 EXE: python build_exe.py")
        print(f"  2. 创建 Tag: git tag -a v{VERSION}")
        print(f"  3. 推送 Tag: git push origin v{VERSION}")
        print(f"  4. 创建 Release: gh release create v{VERSION}")
        print(f"  5. 上传资产: {RELEASE_EXE_NAME}")
        return

    # 步骤 1: 构建 EXE
    if not args.skip_build:
        build_exe()
    else:
        print(f"\n{GREEN}=== 步骤 1: 跳过构建 ==={RESET}")
        if not os.path.exists(DIST_PATH):
            print(f"{RED}错误: 未找到 {DIST_PATH}，请先执行 python build_exe.py{RESET}")
            sys.exit(1)
        # 确保 releases 目录也有
        os.makedirs(RELEASES_DIR, exist_ok=True)
        import shutil
        shutil.copy2(DIST_PATH, RELEASE_EXE_PATH)

    # 步骤 2-3: 创建 tag 和 release
    create_release(gh_path)


if __name__ == "__main__":
    main()
