#!/usr/bin/env python3
"""Install this skill without changing Codex settings or student workspaces."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
FILES = ("SKILL.md", "VERSION", "agents", "references", "assets", "scripts/workspace.py", "scripts/share.py")


def install(destination, update=False):
    destination = Path(destination).expanduser().resolve()
    if destination == ROOT or ROOT in destination.parents or destination in ROOT.parents:
        raise ValueError("ソースと重なる場所にはインストールできません")
    for name in FILES:
        if not (ROOT / name).exists():
            raise ValueError(f"配布ファイルが不足しています: {name}")
    if destination.exists() and not update:
        raise ValueError("既にインストールされています。更新する場合は --update を指定してください")
    if destination.exists() and not (destination / "SKILL.md").is_file():
        raise ValueError("スキルではない既存ディレクトリは変更しません")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".theme-advice-install-", dir=destination.parent))
    backup = None
    previous = None
    installed = False
    try:
        for name in FILES:
            source, target = ROOT / name, staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
        if destination.exists():
            suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]
            base = destination.with_name(destination.name + ".backup-" + suffix)
            backup = Path(shutil.make_archive(str(base), "zip", root_dir=destination))
            previous = staging.with_name(staging.name + ".previous")
            destination.rename(previous)
        staging.rename(destination)
        installed = True
        return destination, backup
    except OSError:
        if previous is not None and previous.exists() and not destination.exists():
            previous.rename(destination)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        if installed and previous is not None and previous.exists():
            shutil.rmtree(previous)


def main(argv=None):
    parser = argparse.ArgumentParser(description="theme-advice-skill をCodexのユーザースキルに導入します")
    parser.add_argument("--dest", type=Path, default=Path.home() / ".agents/skills/theme-advice-skill")
    parser.add_argument("--update", action="store_true", help="既存スキルをバックアップして更新")
    args = parser.parse_args(argv)
    try:
        destination, backup = install(args.dest, args.update)
        print(f"インストールしました: {destination}")
        if backup:
            print(f"以前のスキルを保持しました: {backup}")
        print("Codexで /skills を開き、theme-advice-skill を確認してください。")
        return 0
    except (OSError, ValueError) as exc:
        print(f"インストールできませんでした: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
