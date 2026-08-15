#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eco-sync：个人 AI 使用生态双向同步脚本。

设计目标
--------
把"设备上的 AI 生态"（全局 agent 规则文件 + 全局 skills）与 kevin-AI-studio
公开仓库中的脱敏副本做双向同步，保证多设备之间生态一致、公开仓库不泄漏本机信息。

三个模式
--------
status  只读对比，输出每个生态文件相对仓库 HEAD 的状态与建议动作。
push    设备 -> 仓库：快进 pull 后按三路比较结果把设备变动（自动脱敏）写入仓库
        并 commit + push。
pull    仓库 -> 设备：快进 pull 后把仓库副本渲染回本机值写入设备，并校验 symlink。

三路比较（防静默覆盖的核心）
----------------------------
基线不是单一快照，而是 pull 前后的两个 HEAD：
* old_base = 同步动作前仓库 HEAD 的镜像（渲染回本机视角）
* new_base = 快进 pull 后仓库 HEAD 的镜像（渲染回本机视角）
* device  = 设备端当前内容

判定矩阵（规则文件与 skill 文件共用）：
* device == new_base                 -> UNCHANGED（设备内容已与仓库一致）
* 仓库没动（old_base == new_base）且 device 不同 -> PUSH（纯本地改动）
* 仓库动过且 device == old_base     -> PULL（设备落后，仓库前进）
* 仓库动过且 device != old_base/new_base -> CONFLICT（两边都改，必须显式选方向）

只有显式 --force local|repo 才能解 CONFLICT；除此之外任何覆盖都不发生。

安全边界
--------
* 脱敏渲染：本机值（用户名 / vault 路径）<-> 公开占位符（<your-username> /
  <second-brain-path>）；先替换完整路径、再替换用户名，防止顺序破坏路径串。
* push 落盘前对仓库生态文件全量扫描：残留本机用户名、vault 路径、家目录形式
  路径或常见凭据模式时直接中止，绝不提交。
* 删除语义默认关闭（只增改不删），显式 --prune 才允许删除，防止设备间互删。
* push 前要求仓库工作区生态文件干净，防止覆盖仓库侧手改内容。

依赖：仅 Python 3 标准库，无第三方包，跨设备可直接运行。
"""

import argparse
import getpass
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 生态范围常量
# ---------------------------------------------------------------------------
# 宿主全局规则文件映射：(设备端绝对路径, 仓库端相对路径)。
# 三个宿主的本机文件必须逐字节一致（全局同步规则），仓库端三份镜像同样
# 逐字节一致，仅占位符与本机版不同。
HOST_RULE_FILES = [
    ("~/.claude/CLAUDE.md", "global/CLAUDE.md"),
    ("~/.codex/AGENTS.md", "global/AGENTS.md"),
    ("~/.dsh/AGENTS.md", "global/AGENTS.dsh.md"),
]

# skills 实体目录：设备端 Codex 全局目录，仓库端 skills/ 目录。
SKILLS_HOST_DIR = "~/.agents/skills"
SKILLS_REPO_DIR = "skills"

# Claude Code 全局 skills 目录：通过 symlink 复用 Codex 实体，不入库、只校验。
CLAUDE_SKILLS_DIR = "~/.claude/skills"

# 递归对比 skills 时无条件忽略的路径片段（本机运行时产物）。
IGNORED_PARTS = {"__pycache__", ".git", ".DS_Store"}
IGNORED_SUFFIXES = (".pyc",)

# eco-sync 自身：仓库级 skill，不参与设备全局生态同步（见 compare_skills）。
ECO_SYNC_NAME = "eco-sync"

# 公开仓库中的脱敏占位符（与仓库 README / 全局规则约定一致）。
PLACEHOLDER_USER = "<your-username>"
PLACEHOLDER_VAULT = "<second-brain-path>"

# 安全扫描使用的常见凭据模式；命中即拒绝写入仓库。
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"hf_[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]

# 状态枚举：三路比较结果与后续动作的依据。
UNCHANGED = "UNCHANGED"          # 设备与仓库一致
PUSH = "PUSH"                    # 设备有新内容，push 方向应用
PULL = "PULL"                    # 仓库有新内容，pull 方向应用
CONFLICT = "CONFLICT"            # 两边都改，需 --force 选方向
DELETED_LOCAL = "DELETED_LOCAL"  # 设备端缺失（仓库有）
DELETED_REPO = "DELETED_REPO"    # 仓库端缺失（设备有）


class LocalValues:
    """设备端本机值：用户名与 Second Brain vault 路径。

    两者不硬编码：vault 路径从任一宿主全局规则文件的 Path Guard 行正则提取，
    用户名从 vault 路径推导；同一脚本在多台设备、不同家目录下都能工作，
    且公开仓库中不存在任何本机值。
    """

    def __init__(self, host_files):
        self.username = None
        self.vault = None
        self._detect(host_files)

    def _detect(self, host_files):
        # Path Guard 行形如：将 `/home/<user>/Documents/second-brain` 替换为...
        guard_re = re.compile(r"/home/[^/\s]+/Documents/second-brain")
        for spec, _ in host_files:
            path = Path(spec).expanduser()
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            m = guard_re.search(text)
            if m:
                self.vault = m.group(0)
                self.username = self.vault.split("/")[2]
                return
        # 兜底：无法提取时用当前登录用户名，vault 保持 None（渲染退化为只替换用户名）
        self.username = getpass.getuser()
        if not self.vault:
            raise SystemExit(
                "无法从宿主全局规则文件中提取 Second Brain vault 路径，"
                "请确认 ~/.dsh/AGENTS.md 等文件中的 Second Brain Path Guard 段落存在。"
            )


def sha256_file(path):
    """计算单个文件的 SHA-256；文件不存在返回 None。"""
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def should_ignore(rel):
    """skills 递归对比时的忽略规则：缓存目录、pyc、编辑器噪声。"""
    parts = set(Path(rel).parts)
    if parts & IGNORED_PARTS:
        return True
    if rel.endswith(IGNORED_SUFFIXES):
        return True
    return False


def is_eco_sync_rel(rel):
    """判断相对路径是否属于 eco-sync 自身（顶层目录或其子文件）。"""
    return rel == ECO_SYNC_NAME or rel.startswith(ECO_SYNC_NAME + "/")


def scan_files(root):
    """递归收集目录下全部文件的 {相对路径: sha256}；目录不存在返回 {}。

    用相对路径做键，保证设备端与仓库端可以用同一套字典做差集比较。
    """
    root = Path(root)
    if not root.is_dir():
        return {}
    out = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(root))
        if should_ignore(rel):
            continue
        out[rel] = sha256_file(p)
    return out


def local_to_mirror(text, values):
    """本机 -> 镜像：先替换完整 vault 路径，再替换用户名，防止顺序破坏路径串。"""
    t = text
    if values.vault:
        t = t.replace(values.vault, PLACEHOLDER_VAULT)
    if values.username:
        t = t.replace(values.username, PLACEHOLDER_USER)
    return t


def mirror_to_local(text, values):
    """镜像 -> 本机：把公开占位符渲染回本机值。"""
    t = text
    if values.vault:
        t = t.replace(PLACEHOLDER_VAULT, values.vault)
    if values.username:
        t = t.replace(PLACEHOLDER_USER, values.username)
    return t


# ---------------------------------------------------------------------------
# Git 工具函数（全部经由 subprocess 调用 git，不依赖任何 Python Git 包）
# ---------------------------------------------------------------------------
class GitError(RuntimeError):
    """git 命令失败的受控异常。"""


def run_git(repo, *args, check=True):
    """在仓库目录内执行 git 命令，返回 stdout 文本。"""
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if check and proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def run_git_bytes(repo, *args):
    """以字节口径执行 git 命令并返回原始 stdout。

    用于内容 hash 计算：text=True 会做 universal newlines 转换（\r\n -> \n），
    导致 hash 与设备端原始字节不一致，因此 hash 路径必须使用本函数。
    """
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return proc.stdout


def find_repo():
    """定位并验证仓库：eco-sync 是仓库级 skill，只允许在 kevin-AI-studio 仓库内运行。

    从当前目录向上查找 git 仓库根，然后验证仓库身份：remote origin URL 含
    kevin-AI-studio，或仓库根目录名恰为 kevin-AI-studio；两者都不满足即拒绝
    执行，防止在其他仓库或普通目录误触发生态同步（用户明确要求只有本仓库
    才能改动 AI 生态副本）。
    """
    cwd = Path.cwd()
    root = None
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".git").exists():
            root = parent
            break
    if root is None:
        raise SystemExit(
            "eco-sync 是 kevin-AI-studio 仓库级 skill，请在仓库目录内运行。"
        )
    url = ""
    try:
        url = run_git(root, "config", "--get", "remote.origin.url")
    except GitError:
        url = ""
    if root.name == "kevin-AI-studio" or "kevin-AI-studio" in url:
        run_git(root, "rev-parse", "--is-inside-work-tree")
        return root
    raise SystemExit("当前仓库不是 kevin-AI-studio，拒绝执行生态同步。")


def git_show(repo, rev, repo_rel):
    """读取仓库某修订中文件的原始文本；文件在该修订不存在时返回 None。

    用字节口径读取后按 UTF-8 解码，保留完整内容（含尾换行），保证与设备端
    Path.read_text 得到的文本逐字一致；文本口径的 run_git 会 strip 首尾空白，
    导致规则文件比较因尾换行差异误报 PUSH。
    """
    try:
        raw = run_git_bytes(repo, "show", f"{rev}:{repo_rel}")
    except subprocess.CalledProcessError:
        return None
    return raw.decode("utf-8")


def head_rule_local(repo, rev, repo_rel, values):
    """读取仓库某修订的镜像并渲染回本机视角，作为三路比较基线。"""
    raw = git_show(repo, rev, repo_rel)
    if raw is None:
        return None
    return mirror_to_local(raw, values)


def head_skills_files(repo, rev):
    """读取仓库某修订中 skills/ 的文件清单与 hash。

    通过 git ls-tree 列出该修订 skills/ 的 blob，再用字节口径 git show 计算
    hash，与设备端 scan_files 的原始字节 hash 保持同一口径。
    """
    out = {}
    try:
        listing = run_git(repo, "ls-tree", "-r", "--name-only", rev, SKILLS_REPO_DIR)
    except GitError:
        return {}
    for line in listing.splitlines():
        rel_in_repo = line.strip()
        if not rel_in_repo:
            continue
        # 去掉 skills/ 前缀得到与 scan_files 一致的相对路径
        rel = rel_in_repo[len(SKILLS_REPO_DIR) + 1:]
        if should_ignore(rel):
            continue
        try:
            content = run_git_bytes(repo, "show", f"{rev}:{rel_in_repo}")
        except subprocess.CalledProcessError:
            continue
        out[rel] = hashlib.sha256(content).hexdigest()
    return out


def pull_ff_only(repo):
    """快进式拉取远端；非快进（本地分叉）直接报错，避免隐式合并。"""
    run_git(repo, "pull", "--ff-only", "origin", "master")


def eco_files_clean(repo):
    """确认仓库工作区中生态文件无未提交改动，防止同步覆盖用户手改内容。"""
    out = run_git(repo, "status", "--porcelain", "--", "global", SKILLS_REPO_DIR)
    return out.strip() == ""


# ---------------------------------------------------------------------------
# 三路比较
# ---------------------------------------------------------------------------
class Item:
    """一个被比较的生态单元（规则文件或 skill 文件）的完整状态。"""

    def __init__(self, kind, name, device_text=None, repo_text=None):
        self.kind = kind
        self.name = name
        self.device_text = device_text
        self.repo_text = repo_text


def classify(device, old_base, new_base):
    """三路状态判定矩阵。

    device   = 设备端当前内容（规则文件为文本，skill 文件为 hash 字符串；None 表示缺失）
    old_base = 同步动作前仓库基线（同口径；None 表示仓库旧修订中没有该文件）
    new_base = 快进 pull 后仓库基线（同口径；None 表示仓库新修订中没有该文件）
    """
    if device is None and new_base is None:
        return UNCHANGED
    if new_base is None:
        # 仓库从未有过（或已被删）：设备有而仓库无
        return DELETED_REPO
    if device is None:
        return DELETED_LOCAL
    if device == new_base:
        return UNCHANGED
    repo_changed = old_base is not None and old_base != new_base
    if repo_changed:
        if device == old_base:
            return PULL
        return CONFLICT
    return PUSH


def compare_rules(device_texts, repo, old_head, new_head, values):
    """对三个宿主规则文件做三路比较，返回 Item 列表。"""
    items = []
    for host_spec, repo_rel in HOST_RULE_FILES:
        host_path = str(Path(host_spec).expanduser())
        device = device_texts.get(host_path)
        old_base = head_rule_local(repo, old_head, repo_rel, values)
        new_base = head_rule_local(repo, new_head, repo_rel, values)
        kind = classify(device, old_base, new_base)
        if kind in (PUSH, CONFLICT):
            items.append(Item(kind, repo_rel, device_text=device))
        elif kind == PULL:
            items.append(Item(kind, repo_rel, repo_text=git_show(repo, new_head, repo_rel)))
        elif kind == DELETED_LOCAL:
            items.append(Item(kind, repo_rel, repo_text=git_show(repo, new_head, repo_rel)))
        elif kind == DELETED_REPO:
            items.append(Item(kind, repo_rel, device_text=device))
        else:
            items.append(Item(kind, repo_rel))
    return items


def compare_skills(device_files, old_files, new_files):
    """对 skills 文件做三路比较（hash 口径），返回 Item 列表。

    三个参数都是 {相对路径: sha256}；old/new 分别为 pull 前后仓库 HEAD 的树。

    eco-sync 自身从本比较中排除：它是仓库级 skill，权威源在仓库 skills/ 内、
    运行时实体在仓库 .agents/skills/ 与 .claude/skills/，不属于设备全局生态，
    因此不参与设备与仓库之间的 skills 同步循环（否则 pull 会把它复制回设备
    全局目录、push --prune 会删掉仓库权威源）。
    """
    items = []
    all_names = set(device_files) | set(old_files) | set(new_files)
    for rel in sorted(all_names):
        if is_eco_sync_rel(rel):
            continue
        device = device_files.get(rel)
        old_base = old_files.get(rel)
        new_base = new_files.get(rel)
        kind = classify(device, old_base, new_base)
        if kind == UNCHANGED:
            continue
        items.append(Item(kind, rel))
    return items


# ---------------------------------------------------------------------------
# 安全扫描
# ---------------------------------------------------------------------------
def security_scan(repo, values):
    """扫描仓库工作区全部生态文件：残留本机值或凭据模式即报错。

    本函数是 push 的最终闸门：即使渲染逻辑出错，任何本机值也不得进入公开仓库。
    """
    offenders = []
    roots = [Path(repo) / "global", Path(repo) / SKILLS_REPO_DIR]
    needles = []
    if values.username:
        needles.append(values.username)
    if values.vault:
        needles.append(values.vault)
    if values.username:
        needles.append("/home/" + values.username)
    for root in roots:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*")):
            if not p.is_file() or should_ignore(str(p.relative_to(root))):
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            for n in needles:
                if n and n in text:
                    offenders.append(f"{p}: 本机值泄漏 {n}")
                    break
            for pat in SECRET_PATTERNS:
                if pat.search(text):
                    offenders.append(f"{p}: 凭据模式 {pat.pattern}")
                    break
    if offenders:
        raise SystemExit("安全扫描失败，已中止同步：\n  " + "\n  ".join(offenders))


# ---------------------------------------------------------------------------
# 计划输出与执行
# ---------------------------------------------------------------------------
def print_plan(items, label):
    """按类别打印变更计划，返回 (可执行项数, 冲突项数)。"""
    print(f"== 变更计划（{label}）==")
    acted = 0
    conflicts = 0
    for it in items:
        if it.kind == UNCHANGED:
            continue
        print(f"  {it.kind:<14} {it.name}")
        if it.kind == CONFLICT:
            conflicts += 1
        else:
            acted += 1
    return acted, conflicts


def apply_push(repo, values, rules_items, skills_items, prune):
    """把 push 方向的动作落盘到仓库工作区。

    规则文件：设备文本脱敏渲染后写镜像；skills：逐文件复制；删除仅 --prune 生效。
    """
    repo_skills = Path(repo) / SKILLS_REPO_DIR
    host_skills = Path(SKILLS_HOST_DIR).expanduser()
    for it in rules_items:
        if it.kind in (PUSH, DELETED_REPO):
            target = Path(repo) / it.name
            target.write_text(
                local_to_mirror(it.device_text, values), encoding="utf-8", newline="\n"
            )
    for it in skills_items:
        if it.kind in (PUSH, DELETED_REPO):
            src = host_skills / it.name
            dst = repo_skills / it.name
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        elif it.kind == DELETED_LOCAL and prune:
            run_git(repo, "rm", "-r", "--", f"{SKILLS_REPO_DIR}/{it.name}")


def apply_pull(repo, values, rules_items, skills_items, prune):
    """把 pull 方向的动作落盘到设备端。

    规则文件：只写被判定为 PULL / DELETED_LOCAL 的宿主文件（设备端规则文件缺失
    时同样写回）；设备有本地改动的文件绝不覆盖。skills：仓库 -> 设备复制；
    Claude symlink 缺失自动创建，目录冲突只报告。
    """
    host_skills = Path(SKILLS_HOST_DIR).expanduser()
    repo_skills = Path(repo) / SKILLS_REPO_DIR
    rule_repos = {it.name for it in rules_items}  # 本次要处理的规则镜像相对路径
    for host_spec, repo_rel in HOST_RULE_FILES:
        if repo_rel not in rule_repos:
            continue  # 设备无改动且内容一致的文件不重写，避免触碰 mtime
        raw = git_show(repo, "HEAD", repo_rel)
        if raw is None:
            continue
        Path(host_spec).expanduser().write_text(
            mirror_to_local(raw, values), encoding="utf-8", newline="\n"
        )
    for it in skills_items:
        if it.kind in (PULL, DELETED_LOCAL):
            src = repo_skills / it.name
            dst = host_skills / it.name
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        elif it.kind == DELETED_REPO and prune:
            p = host_skills / it.name
            if p.is_file():
                p.unlink()
    # 校验 Claude Code symlink：缺失的自动创建，指向 Codex 实体目录
    claude_dir = Path(CLAUDE_SKILLS_DIR).expanduser()
    claude_dir.mkdir(parents=True, exist_ok=True)
    for p in sorted(host_skills.iterdir()):
        if not p.is_dir():
            continue
        link = claude_dir / p.name
        if link.is_symlink():
            continue
        if link.exists():
            print(f"  注意：{link} 不是 symlink，未自动处理，请手动检查。")
            continue
        link.symlink_to(p)
        print(f"  已创建 symlink：{link}")


def resolve_force(items, force, direction):
    """按 --force 把 CONFLICT 项转化为确定方向的动作。

    push 方向：--force local 时冲突项当作 PUSH（仓库被设备覆盖）；--force repo
    时冲突项直接跳过（保持仓库现状）。pull 方向对称：--force repo 时当作 PULL
    （设备被仓库覆盖）；--force local 时跳过（保持设备现状）。
    未指定 --force 时冲突项原样保留，由调用方报告后中止。

    返回 (resolved_items, remaining_conflicts)。
    """
    resolved = []
    remaining = 0
    for it in items:
        if it.kind == CONFLICT:
            if direction == "push":
                if force == "local":
                    resolved.append(Item(PUSH, it.name, device_text=it.device_text))
                    continue
                if force == "repo":
                    print(f"  按 --force repo 跳过冲突项（保持仓库）：{it.name}")
                    continue
            else:  # pull
                if force == "repo":
                    resolved.append(Item(PULL, it.name, repo_text=it.repo_text))
                    continue
                if force == "local":
                    print(f"  按 --force local 跳过冲突项（保持设备）：{it.name}")
                    continue
            remaining += 1
        resolved.append(it)
    return resolved, remaining


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="个人 AI 使用生态双向同步（kevin-AI-studio 仓库级）")
    parser.add_argument("mode", choices=["status", "push", "pull"])
    parser.add_argument("--yes", action="store_true", help="执行写入；缺省 dry-run")
    parser.add_argument(
        "--force", choices=["local", "repo"],
        help="冲突时选定方向：local=设备为准，repo=仓库为准",
    )
    parser.add_argument("--prune", action="store_true", help="允许删除对方已不存在的 skill")
    args = parser.parse_args()

    repo = find_repo()
    values = LocalValues(HOST_RULE_FILES)
    print(f"仓库：{repo}")
    print(f"本机值：username={values.username} vault={values.vault}")

    # 记录 pull 前的 HEAD，作为三路比较的旧基线
    old_head = run_git(repo, "rev-parse", "HEAD")
    new_head = old_head

    if args.mode in ("push", "pull"):
        pull_ff_only(repo)
        new_head = run_git(repo, "rev-parse", "HEAD")
        if args.mode == "push" and not eco_files_clean(repo):
            raise SystemExit("仓库工作区中 global/ 或 skills/ 存在未提交改动，请先处理再同步。")

    device_texts = {}
    for spec, _ in HOST_RULE_FILES:
        p = Path(spec).expanduser()
        device_texts[str(p)] = p.read_text(encoding="utf-8") if p.is_file() else None

    rules_items = compare_rules(device_texts, repo, old_head, new_head, values)
    device_skill_files = scan_files(Path(SKILLS_HOST_DIR).expanduser())
    old_skill_files = head_skills_files(repo, old_head)
    new_skill_files = head_skills_files(repo, new_head)
    skills_items = compare_skills(device_skill_files, old_skill_files, new_skill_files)

    if args.mode == "status":
        label = "设备 vs 仓库 HEAD（只读）"
        acted, conflicts = print_plan(rules_items + skills_items, label)
        if acted == 0 and conflicts == 0:
            print("生态副本完全一致，没有差异。")
        return

    if args.mode == "push":
        # push 方向：设备端三个宿主规则文件必须存在，缺失属于异常状态，先中止
        missing_rules = [it for it in rules_items if it.kind == DELETED_LOCAL]
        if missing_rules:
            raise SystemExit(
                "设备端宿主规则文件缺失，请先检查：\n  "
                + "\n  ".join(it.name for it in missing_rules)
            )
        items, remaining = resolve_force(rules_items + skills_items, args.force, "push")
        plan_items = [it for it in items if it.kind in (PUSH, DELETED_REPO, DELETED_LOCAL)]
        acted, conflicts = print_plan(items, "push：设备 -> 仓库")
        if acted == 0 and remaining == 0:
            print("没有需要推送的变更。")
            return
        if not args.yes:
            print("dry-run：未执行任何写入。加 --yes 执行。")
            return
        if remaining:
            raise SystemExit("存在未解决的 CONFLICT，已中止。请用 --force 选定方向或手动处理。")
        r_items = [it for it in plan_items if it.name in {i.name for i in rules_items}]
        s_items = [it for it in plan_items if it.name not in {i.name for i in rules_items}]
        apply_push(repo, values, r_items, s_items, args.prune)
        security_scan(repo, values)
        run_git(repo, "add", "--", "global", SKILLS_REPO_DIR)
        run_git(repo, "commit", "-m", "sync: update AI ecosystem copies")
        run_git(repo, "push", "origin", "master")
        print("已提交并推送。")
        return

    # pull 方向：CONFLICT 仅在 --force repo 时解为 PULL；设备侧纯改动项不动作
    items, remaining = resolve_force(rules_items + skills_items, args.force, "pull")
    plan_items = [it for it in items if it.kind in (PULL, DELETED_LOCAL, DELETED_REPO)]
    acted, conflicts = print_plan(items, "pull：仓库 -> 设备")
    if acted == 0 and remaining == 0:
        print("没有需要拉取的变更。")
        return
    if not args.yes:
        print("dry-run：未执行任何写入。加 --yes 执行。")
        return
    if remaining:
        raise SystemExit("存在未解决的 CONFLICT，已中止。请用 --force 选定方向或手动处理。")
    r_items = [it for it in plan_items if it.name in {i.name for i in rules_items}]
    s_items = [it for it in plan_items if it.name not in {i.name for i in rules_items}]
    apply_pull(repo, values, r_items, s_items, args.prune)
    print("设备端生态已更新。")


if __name__ == "__main__":
    main()
