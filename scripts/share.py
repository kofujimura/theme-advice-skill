#!/usr/bin/env python3
"""Export and explicitly submit one chosen theme; Python standard library only."""

import argparse
import copy
from datetime import datetime
import getpass
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request
from uuid import UUID, uuid4

try:
    from workspace import SKILL_ROOT, load_session, timestamp, write_json
except ImportError:  # Also works when imported independently by tests.
    import importlib.util
    spec = importlib.util.spec_from_file_location("theme_workspace", Path(__file__).with_name("workspace.py"))
    workspace_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(workspace_module)
    SKILL_ROOT, load_session = workspace_module.SKILL_ROOT, workspace_module.load_session
    timestamp, write_json = workspace_module.timestamp, workspace_module.write_json

MAX_BYTES = 65536
SCHEMA = json.loads((SKILL_ROOT / "assets/public-theme.schema.json").read_text(encoding="utf-8"))


def validate_public(value):
    """Validate the subset of JSON Schema used by our shared public schema."""
    errors = []

    def check(item, schema, path):
        if "$ref" in schema:
            schema = SCHEMA["$defs"][schema["$ref"].rsplit("/", 1)[1]]
        if "const" in schema and item != schema["const"]:
            errors.append(f"{path}: 対応しない値です")
        if "enum" in schema and item not in schema["enum"]:
            errors.append(f"{path}: 対応しない値です")
        kinds = schema.get("type")
        if kinds:
            kinds = [kinds] if isinstance(kinds, str) else kinds
            actual = "null" if item is None else "object" if isinstance(item, dict) else "array" if isinstance(item, list) else "string" if isinstance(item, str) else "other"
            if actual not in kinds:
                errors.append(f"{path}: 型が違います")
                return
        if isinstance(item, dict):
            properties = schema.get("properties", {})
            for key in schema.get("required", []):
                if key not in item:
                    errors.append(f"{path}.{key}: 必須です")
            if schema.get("additionalProperties") is False:
                for key in item.keys() - properties.keys():
                    errors.append(f"{path}.{key}: 共有形式にない項目です")
            for key in item.keys() & properties.keys():
                check(item[key], properties[key], f"{path}.{key}")
        elif isinstance(item, list):
            if len(item) < schema.get("minItems", 0) or len(item) > schema.get("maxItems", sys.maxsize):
                errors.append(f"{path}: 件数が範囲外です")
            if schema.get("uniqueItems") and len({json.dumps(i, sort_keys=True, ensure_ascii=False) for i in item}) != len(item):
                errors.append(f"{path}: 重複があります")
            for index, child in enumerate(item):
                check(child, schema.get("items", {}), f"{path}[{index}]")
        elif isinstance(item, str):
            if len(item) < schema.get("minLength", 0) or len(item) > schema.get("maxLength", sys.maxsize):
                errors.append(f"{path}: 文字数が範囲外です")
            if "pattern" in schema and not re.search(schema["pattern"], item):
                errors.append(f"{path}: 形式が違います")
            try:
                if schema.get("format") == "uuid":
                    UUID(item)
                    if not re.fullmatch(r"[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", item):
                        raise ValueError()
                elif schema.get("format") == "date-time":
                    parsed = datetime.fromisoformat(item.replace("Z", "+00:00"))
                    if parsed.tzinfo is None or "T" not in item.upper():
                        raise ValueError()
                elif schema.get("format") == "uri":
                    parsed = urlsplit(item)
                    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                        raise ValueError()
            except ValueError:
                errors.append(f"{path}: {schema.get('format')} 形式が必要です")

    check(value, SCHEMA, "theme.json")
    if not errors:
        sources = {source["id"]: source for source in value["sources"]}
        if len(sources) != len(value["sources"]):
            errors.append("資料IDが重複しています")
        theme = value["theme"]
        for refs, evidence in ((theme["source_ids"], theme["novelty"]["status"] == "search_scoped"),
                               (theme["technology"]["source_ids"], theme["technology"]["availability"] == "verified")):
            if any(identifier not in sources for identifier in refs):
                errors.append("存在しない資料IDが含まれています")
            if evidence and not any(sources.get(identifier, {}).get("read_level") in ("full_text", "abstract") for identifier in refs):
                errors.append("確認済みの根拠となる資料が必要です")
    if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > MAX_BYTES:
        errors.append("共有JSONは64 KiB以内にしてください")
    return errors


def export_theme(workspace):
    session = load_session(workspace)
    nickname = session["student"].get("nickname")
    if not isinstance(nickname, str) or not nickname.strip():
        raise ValueError("公開時に表示するニックネームを学生本人に聞いてください")
    selected = session["selected_candidate_id"]
    if selected is None:
        raise ValueError("共有する候補を学生本人が選んでから保存してください")
    candidate = next(item for item in session["candidates"] if item["id"] == selected)
    theme = {key: copy.deepcopy(candidate[key]) for key in (
        "title", "rq", "interest_connection", "contribution_types", "source_ids", "technology", "evaluation", "pilot", "open_questions")}
    theme["novelty"] = {"status": candidate["novelty_status"], "claim": candidate["novelty_claim"]}
    source_ids = set(candidate["source_ids"] + candidate["technology"]["source_ids"])
    sources = [{key: copy.deepcopy(source.get(key)) for key in (
        "id", "title", "url", "kind", "read_level", "checked_at", "takeaway")}
        for source in session["sources"] if source["id"] in source_ids]
    payload = {"schema_version": "1.0", "id": str(uuid4()), "created_at": timestamp(),
               "author": {"nickname": nickname.strip()}, "theme": theme, "sources": sources}
    path = workspace / "theme.json"
    # Keep the same ID and bytes on repeated exports of unchanged content.
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if not validate_public(previous) and all(previous[key] == payload[key] for key in ("schema_version", "author", "theme", "sources")):
            return path, previous
        # Keep an immutable copy before exporting a revised theme with a new ID.
        archive = workspace / "shared-themes"
        archive.mkdir(exist_ok=True)
        backup = archive / (previous.get("id", "previous") + ".json")
        # Do not use an unvalidated value as a filename.
        if validate_public(previous):
            raise ValueError("既存theme.jsonの形式が壊れています。上書きせず確認してください")
        if not backup.exists():
            write_json(backup, previous)
    errors = validate_public(payload)
    if errors:
        raise ValueError("\n".join(errors))
    write_json(path, payload)
    return path, payload


def site_url(value, allow_local_http=False):
    if not isinstance(value, str):
        raise ValueError("送信先が未設定です。先生のサイトURLを設定してください")
    parsed = urlsplit(value)
    local = parsed.hostname in ("localhost", "127.0.0.1", "::1")
    if parsed.scheme != "https" and not (allow_local_http and local and parsed.scheme == "http"):
        raise ValueError("送信先はHTTPSのサイトURLにしてください（開発時だけlocalhost HTTPを指定可能）")
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ValueError("送信先にはサイトのルートURLを指定してください")
    return value.rstrip("/")


def configuration(workspace):
    result = json.loads((SKILL_ROOT / "assets/site-config.json").read_text(encoding="utf-8"))
    path = workspace / ".send-config.json"
    if path.exists():
        result.update(json.loads(path.read_text(encoding="utf-8")))
    if os.environ.get("THEME_SITE_URL"):
        result["site_url"] = os.environ["THEME_SITE_URL"]
    if os.environ.get("THEME_SUBMIT_TOKEN"):
        result["submit_token"] = os.environ["THEME_SUBMIT_TOKEN"]
    return result


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def submit(workspace, allow_local_http=False):
    config = configuration(workspace)
    base = site_url(config.get("site_url"), allow_local_http)
    token = config.get("submit_token")
    if not isinstance(token, str) or len(token) < 24 or any(char.isspace() for char in token):
        raise ValueError("ゼミの送信キーが未設定です。configure --prompt-token または環境変数で設定してください")
    # Do not regenerate here: this sends exactly the reviewable exported artifact.
    path = workspace / "theme.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_public(payload)
    if errors:
        raise ValueError("\n".join(errors))
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    receipt = {"id": payload["id"], "site_url": base, "attempted_at": timestamp(), "status": "sending"}
    receipt_path = workspace / "submission.json"
    write_json(receipt_path, receipt)
    request = Request(base + "/api/themes", data=body, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json", "Authorization": "Bearer " + token})
    try:
        with build_opener(NoRedirects()).open(request, timeout=30) as response:
            result = json.loads(response.read(MAX_BYTES + 1).decode("utf-8"))
            if response.status not in (200, 201) or result.get("id") != payload["id"]:
                raise ValueError("送信先の応答を確認できませんでした")
        receipt.update(status="sent", received_at=timestamp(), duplicate=bool(result.get("duplicate")),
                       view_url=base + "/?theme=" + payload["id"])
        write_json(receipt_path, receipt)
        return receipt
    except HTTPError as exc:
        # A storage-side failure could have occurred after writing. Same-ID retry is safe.
        receipt["status"] = "unknown" if exc.code >= 500 else "rejected"
        receipt["http_status"] = exc.code
        write_json(receipt_path, receipt)
        explanation = {401: "送信キーが違います", 409: "同じIDの別の内容が既にあります", 413: "JSONのサイズが大きすぎます",
                       422: "JSONの形式が受け付けられません", 503: "サイトの保存先または送信キーが未設定です"}.get(exc.code, "送信先を確認してください")
        raise ValueError(f"送信を確認できませんでした（HTTP {exc.code}）。{explanation}") from None
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        receipt["status"] = "unknown"
        write_json(receipt_path, receipt)
        raise ValueError("送信の成否が未確認です。同じtheme.jsonを再送できます。送信先と接続を確認してください") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description="ニックネーム・共有JSON・明示的なテーマ送信")
    parser.add_argument("--workspace", type=Path, default=Path("theme-workspace"))
    commands = parser.add_subparsers(dest="command", required=True)
    nickname = commands.add_parser("nickname")
    nickname.add_argument("name")
    config = commands.add_parser("configure")
    config.add_argument("--site-url")
    config.add_argument("--prompt-token", action="store_true", help="送信キーを画面に表示せず入力して保存")
    config.add_argument("--allow-local-http", action="store_true")
    commands.add_parser("export")
    send = commands.add_parser("send")
    send.add_argument("--allow-local-http", action="store_true")
    commands.add_parser("status")
    args = parser.parse_args(argv)
    workspace = args.workspace.expanduser().resolve()
    try:
        if args.command == "nickname":
            session = load_session(workspace)
            name = args.name.strip()
            if not name or len(name) > 40:
                raise ValueError("ニックネームは1〜40文字で指定してください")
            session["student"]["nickname"] = name
            session["updated_at"] = timestamp()
            write_json(workspace / "session.json", session)
            print(f"ニックネームを保存しました: {name}")
        elif args.command == "configure":
            workspace.mkdir(parents=True, exist_ok=True)
            path = workspace / ".send-config.json"
            saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            if args.site_url:
                saved["site_url"] = site_url(args.site_url, args.allow_local_http)
            if args.prompt_token:
                if not sys.stdin.isatty():
                    raise ValueError("送信キーは対話可能なターミナルで入力するか、環境変数を利用してください")
                token = getpass.getpass("ゼミの送信キー（入力は表示されません）: ")
                if len(token) < 24 or any(char.isspace() for char in token):
                    raise ValueError("送信キーの形式を確認してください")
                saved["submit_token"] = token
            if not saved:
                raise ValueError("設定するURLまたは --prompt-token を指定してください")
            write_json(path, saved)
            path.chmod(0o600)
            print(f"送信設定を保存しました: {path}（キーは表示しません）")
        elif args.command == "export":
            path, payload = export_theme(workspace)
            print(f"共有JSONを保存しました: {path}\nニックネーム: {payload['author']['nickname']}\nテーマ: {payload['theme']['title']}")
        elif args.command == "send":
            receipt = submit(workspace, args.allow_local_http)
            print("送信を確認しました" + "（同じ投稿は既に受け付け済み）" * receipt["duplicate"])
            print(receipt["view_url"])
        else:
            config = configuration(workspace)
            print(f"送信先: {config.get('site_url') or '未設定'} / キー: {'設定済み' if config.get('submit_token') else '未設定'}")
            path = workspace / "submission.json"
            if path.exists():
                receipt = json.loads(path.read_text(encoding="utf-8"))
                print(f"最後の送信: {receipt['status']} / ID: {receipt['id']}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"共有処理を完了できませんでした: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
