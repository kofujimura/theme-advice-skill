#!/usr/bin/env python3
"""Local session scaffolding, consistency checks, and checkpoints (stdlib only)."""

import argparse
import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
from uuid import uuid4

SKILL_ROOT = Path(__file__).resolve().parents[1]
STAGES = {"explore", "diverge", "focus", "investigate", "plan", "proposal"}
AXES = {"interest", "question", "novelty", "evaluation", "feasibility", "ownership"}


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path, data):
    """Replace a JSON file atomically in the same filesystem."""
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(prefix=".session-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_session(data):
    """Check shape and evidence references; does not verify research claims."""
    errors = []

    def error(path, message):
        errors.append(f"{path}: {message}")

    def obj(value, path):
        if not isinstance(value, dict):
            error(path, "object が必要です")
            return {}
        return value

    def array(value, path):
        if not isinstance(value, list):
            error(path, "array が必要です")
            return []
        return value

    def string(value, path, nullable=False):
        if not isinstance(value, str) and not (nullable and value is None):
            error(path, "string" + " または null" * nullable + " が必要です")

    def strings(value, path):
        values = array(value, path)
        for index, item in enumerate(values):
            string(item, f"{path}[{index}]")
        return values

    def enum(value, choices, path):
        if not isinstance(value, str) or value not in choices:
            error(path, "次のいずれかが必要です: " + ", ".join(sorted(choices)))

    def date(value, path, nullable=False):
        if nullable and value is None:
            return
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("timezone missing")
        except (AttributeError, TypeError, ValueError):
            error(path, "タイムゾーン付き ISO 8601 日時が必要です")

    data = obj(data, "session")
    if data.get("schema_version") != "1.0":
        error("schema_version", "対応する版は 1.0 です")
    string(data.get("skill_version"), "skill_version")
    for key in ("created_at", "updated_at"):
        date(data.get(key), key)
    enum(data.get("stage"), STAGES, "stage")
    environment = obj(data.get("environment"), "environment")
    for key in ("model", "codex_version"):
        string(environment.get(key), f"environment.{key}", nullable=True)
    enum(environment.get("search"), {"unknown", "available", "unavailable"}, "environment.search")
    student = obj(data.get("student"), "student")
    string(student.get("participant_id"), "student.participant_id", nullable=True)
    nickname = student.get("nickname")
    string(nickname, "student.nickname", nullable=True)
    if isinstance(nickname, str) and (not nickname.strip() or len(nickname) > 40):
        error("student.nickname", "1〜40文字のニックネームまたは null が必要です")
    for key in ("interests", "experiences", "constraints"):
        for index, value in enumerate(array(student.get(key), f"student.{key}")):
            path = f"student.{key}[{index}]"
            value = obj(value, path)
            string(value.get("text"), path + ".text")
            enum(value.get("origin"), {"student", "assistant"}, path + ".origin")
            if type(value.get("confirmed_by_student")) is not bool:
                error(path + ".confirmed_by_student", "boolean が必要です")
    strings(student.get("own_words"), "student.own_words")

    sources = {}
    for index, value in enumerate(array(data.get("sources"), "sources")):
        path = f"sources[{index}]"
        value = obj(value, path)
        identifier = value.get("id")
        if not isinstance(identifier, str) or not identifier:
            error(path + ".id", "空でない資料IDが必要です")
        elif identifier in sources:
            error(path + ".id", "資料IDが重複しています")
        else:
            sources[identifier] = value
        for key in ("title", "takeaway"):
            string(value.get(key), path + "." + key)
        enum(value.get("kind"), {"paper", "official", "lab", "artwork", "other"}, path + ".kind")
        enum(value.get("read_level"), {"full_text", "abstract", "snippet", "unread"}, path + ".read_level")
        url = value.get("url")
        if not (isinstance(url, str) and url.startswith(("https://", "http://"))):
            if url is not None or not isinstance(value.get("file"), str) or not value["file"]:
                error(path, "HTTP(S) URL、または url:null とローカル file が必要です")
        date(value.get("checked_at"), path + ".checked_at", nullable=value.get("read_level") == "unread")

    def source_refs(value, path, evidence=False):
        identifiers = strings(value, path)
        for identifier in identifiers:
            if isinstance(identifier, str) and identifier not in sources:
                error(path, f"存在しない資料ID: {identifier}")
        readable = [sources[item] for item in identifiers if isinstance(item, str) and item in sources
                    and sources[item].get("read_level") in ("full_text", "abstract")]
        if evidence and not readable:
            error(path, "確認済みの根拠には、本文または要旨を読んだ資料IDが必要です")

    candidates = {}
    for index, value in enumerate(array(data.get("candidates"), "candidates")):
        path = f"candidates[{index}]"
        value = obj(value, path)
        identifier = value.get("id")
        if not isinstance(identifier, str) or not identifier:
            error(path + ".id", "空でない候補IDが必要です")
        elif identifier in candidates:
            error(path + ".id", "候補IDが重複しています")
        else:
            candidates[identifier] = value
        for key in ("title", "interest_connection", "rq", "novelty_claim", "pilot"):
            string(value.get(key), path + "." + key)
        for index2, item in enumerate(array(value.get("contribution_types"), path + ".contribution_types")):
            enum(item, {"technical", "application", "problem", "artistic"}, path + f".contribution_types[{index2}]")
        enum(value.get("novelty_status"), {"unverified", "search_scoped", "teacher_reviewed"}, path + ".novelty_status")
        source_refs(value.get("source_ids"), path + ".source_ids", value.get("novelty_status") == "search_scoped")
        technology = obj(value.get("technology"), path + ".technology")
        for key in ("capability", "conditions"):
            string(technology.get(key), path + ".technology." + key)
        enum(technology.get("availability"), {"unverified", "verified", "unavailable"}, path + ".technology.availability")
        source_refs(technology.get("source_ids"), path + ".technology.source_ids", technology.get("availability") == "verified")
        evaluation = obj(value.get("evaluation"), path + ".evaluation")
        for key in ("comparison", "procedure", "resources", "limitations"):
            string(evaluation.get(key), path + ".evaluation." + key)
        strings(evaluation.get("metrics"), path + ".evaluation.metrics")
        for key in ("student_feedback", "open_questions"):
            strings(value.get(key), path + "." + key)
        readiness = obj(value.get("readiness"), path + ".readiness")
        for key in AXES:
            enum(readiness.get(key), {"ready", "needs_work", "unknown"}, path + ".readiness." + key)
        if readiness.get("novelty") == "ready" and value.get("novelty_status") == "unverified":
            error(path + ".readiness.novelty", "未調査の新規性を ready にはできません")

    decisions = []
    for index, value in enumerate(array(data.get("decisions"), "decisions")):
        path = f"decisions[{index}]"
        value = obj(value, path)
        decisions.append(value)
        date(value.get("at"), path + ".at")
        enum(value.get("actor"), {"student", "assistant", "teacher"}, path + ".actor")
        enum(value.get("action"), {"propose", "revise", "select", "reject", "reopen", "teacher_feedback"}, path + ".action")
        string(value.get("reason"), path + ".reason")
        string(value.get("student_quote"), path + ".student_quote", nullable=True)
        identifier = value.get("candidate_id")
        if identifier is not None and (not isinstance(identifier, str) or identifier not in candidates):
            error(path + ".candidate_id", "存在する候補IDまたは null が必要です")

    selected = data.get("selected_candidate_id")
    if data.get("stage") == "proposal" and selected is None:
        error("stage", "proposal 段階には本人が選択した候補が必要です。未選択の草案は plan 等で保存できます")
    if selected is not None:
        if not isinstance(selected, str) or selected not in candidates:
            error("selected_candidate_id", "存在する候補IDまたは null が必要です")
        elif not any(item.get("actor") == "student" and item.get("action") == "select"
                     and item.get("candidate_id") == selected for item in decisions):
            error("selected_candidate_id", "本人の選択 (student/select) を decisions に残してください")
    for identifier, value in candidates.items():
        if value.get("novelty_status") == "teacher_reviewed" and not any(
                item.get("actor") == "teacher" and item.get("action") == "teacher_feedback"
                and item.get("candidate_id") == identifier for item in decisions):
            error(f"candidate {identifier}", "教員の実際のコメントを decisions に残してください")

    for index, value in enumerate(array(data.get("searches"), "searches")):
        path = f"searches[{index}]"
        value = obj(value, path)
        date(value.get("at"), path + ".at")
        for key in ("query", "scope", "limitations"):
            string(value.get(key), path + "." + key)
    strings(data.get("next_actions"), "next_actions")
    return errors


def load_session(workspace):
    with (workspace / "session.json").open(encoding="utf-8") as stream:
        data = json.load(stream)
    errors = validate_session(data)
    if errors:
        raise ValueError("\n".join(errors))
    return data


def initialize(workspace):
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / "session.json"
    if path.exists():
        load_session(workspace)
    else:
        data = json.loads((SKILL_ROOT / "assets/session.template.json").read_text(encoding="utf-8"))
        data["skill_version"] = (SKILL_ROOT / "VERSION").read_text().strip()
        data["created_at"] = data["updated_at"] = timestamp()
        errors = validate_session(data)
        if errors:
            raise ValueError("\n".join(errors))
        with path.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    journal = workspace / "journal.md"
    if not journal.exists():
        with journal.open("x", encoding="utf-8") as stream:
            stream.write("# テーマ検討の記録\n\n各回の要点、本人の判断、未確認事項、次の作業を残します。\n")
    return path


def checkpoint(workspace):
    data = copy.deepcopy(load_session(workspace))
    data["updated_at"] = timestamp()
    data["skill_version"] = (SKILL_ROOT / "VERSION").read_text().strip()
    snapshots = workspace / "snapshots"
    snapshots.mkdir(exist_ok=True)
    name = datetime.now(timezone.utc).strftime("session-%Y%m%dT%H%M%SZ-") + uuid4().hex[:8] + ".json"
    target = snapshots / name
    with target.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    write_json(workspace / "session.json", data)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description="テーマ検討のローカル記録を初期化・確認・保存します")
    parser.add_argument("command", choices=["init", "validate", "checkpoint", "status"])
    parser.add_argument("--workspace", type=Path, default=Path("theme-workspace"))
    args = parser.parse_args(argv)
    workspace = args.workspace.expanduser().resolve()
    try:
        if args.command == "init":
            print(f"記録を用意しました（既存記録は保持）: {initialize(workspace)}")
        elif args.command == "checkpoint":
            print(f"チェックポイントを保存しました: {checkpoint(workspace)}")
        else:
            data = load_session(workspace)
            if args.command == "validate":
                print("記録の整合性を確認しました。新規性・出典の真偽は別途確認してください。")
            else:
                print(f"段階: {data['stage']} / 候補: {len(data['candidates'])}件 / 選択: {data['selected_candidate_id'] or '未選択'}")
                for item in data["next_actions"]:
                    print(f"- {item}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"記録を処理できませんでした: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
