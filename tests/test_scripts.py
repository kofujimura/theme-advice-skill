"""Tests for preservation, evidence bookkeeping, and portable installation."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


workspace = module("workspace")
installer = module("install")


def candidate():
    return {
        "id": "C1", "title": "反応を引き継ぐ作品", "interest_connection": "本人の制作への関心",
        "rq": "鑑賞者がどんな体験を記述するか", "contribution_types": ["artistic"],
        "novelty_status": "unverified", "novelty_claim": "既存作品との違いは未調査", "source_ids": [],
        "technology": {"capability": "反応の引き継ぎ", "availability": "unverified", "source_ids": [], "conditions": "未確認"},
        "evaluation": {"comparison": "", "metrics": [], "procedure": "鑑賞体験の記述", "resources": "", "limitations": "少人数の試行"},
        "pilot": "小さな作品で試す", "student_feedback": [],
        "readiness": dict.fromkeys(workspace.AXES, "unknown"), "open_questions": ["既存作品との関係"]
    }


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "相談"
        workspace.initialize(self.path)
        self.data = workspace.load_session(self.path)

    def test_initialization_preserves_existing_japanese_records_and_journal(self):
        self.data["student"]["own_words"] = ["便利さより、気味悪い感じを出したい"]
        workspace.write_json(self.path / "session.json", self.data)
        (self.path / "journal.md").write_text("# 自分の判断\n作品を作りたい\n", encoding="utf-8")
        before = {name: (self.path / name).read_bytes() for name in ("session.json", "journal.md")}
        workspace.initialize(self.path)
        self.assertEqual(before, {name: (self.path / name).read_bytes() for name in before})

    def test_corrupt_existing_session_is_not_reinitialized(self):
        (self.path / "session.json").write_text("broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            workspace.initialize(self.path)
        self.assertEqual((self.path / "session.json").read_text(), "broken")

    def test_checkpoint_keeps_distinct_versions_and_prior_snapshot(self):
        self.data["next_actions"] = ["作品を観察する"]
        workspace.write_json(self.path / "session.json", self.data)
        first = workspace.checkpoint(self.path)
        self.data["next_actions"] = ["先行作品を調べる"]
        workspace.write_json(self.path / "session.json", self.data)
        second = workspace.checkpoint(self.path)
        self.assertNotEqual(first, second)
        self.assertEqual(json.loads(first.read_text())["next_actions"], ["作品を観察する"])
        self.assertEqual(json.loads(second.read_text())["next_actions"], ["先行作品を調べる"])

    def test_selection_requires_actual_student_decision(self):
        self.data["candidates"] = [candidate()]
        self.data["selected_candidate_id"] = "C1"
        self.assertTrue(workspace.validate_session(self.data))
        self.data["decisions"] = [{"at": workspace.timestamp(), "actor": "student", "action": "select",
                                   "candidate_id": "C1", "reason": "本人が選んだ", "student_quote": "作品を作りたい"}]
        self.assertEqual(workspace.validate_session(self.data), [])

    def test_search_scoped_claim_rejects_missing_or_unread_evidence(self):
        item = candidate()
        item["novelty_status"] = "search_scoped"
        item["source_ids"] = ["S1"]
        self.data["candidates"] = [item]
        self.assertTrue(workspace.validate_session(self.data))
        source = {"id": "S1", "kind": "paper", "title": "A prior work", "url": "https://example.org/paper",
                  "read_level": "snippet", "checked_at": workspace.timestamp(), "takeaway": "検索結果のみ"}
        self.data["sources"] = [source]
        self.assertTrue(workspace.validate_session(self.data))
        source["read_level"] = "abstract"
        self.assertEqual(workspace.validate_session(self.data), [])

    def test_technology_availability_requires_read_evidence(self):
        item = candidate()
        item["technology"]["availability"] = "verified"
        self.data["candidates"] = [item]
        self.assertTrue(workspace.validate_session(self.data))

    def test_teacher_review_requires_recorded_teacher_feedback(self):
        item = candidate()
        item["novelty_status"] = "teacher_reviewed"
        self.data["candidates"] = [item]
        self.assertTrue(workspace.validate_session(self.data))
        self.data["decisions"] = [{"at": workspace.timestamp(), "actor": "teacher", "action": "teacher_feedback",
                                  "candidate_id": "C1", "reason": "関連作品を追加調査するようコメント", "student_quote": None}]
        self.assertEqual(workspace.validate_session(self.data), [])

    def test_draft_artistic_candidate_does_not_need_quantitative_metrics(self):
        self.data["candidates"] = [candidate()]
        self.data["stage"] = "plan"
        self.assertEqual(workspace.validate_session(self.data), [])

    def test_inconsistent_novelty_ready_and_unselected_proposal_are_rejected(self):
        item = candidate()
        item["readiness"]["novelty"] = "ready"
        self.data["candidates"] = [item]
        self.assertTrue(workspace.validate_session(self.data))
        item["readiness"]["novelty"] = "unknown"
        self.data["stage"] = "proposal"
        self.assertTrue(workspace.validate_session(self.data))

    def test_malformed_nested_values_report_errors_without_crashing(self):
        for field, bad in (("student", []), ("candidates", "wrong"), ("sources", [None]), ("environment", None)):
            data = copy.deepcopy(self.data)
            data[field] = bad
            self.assertTrue(workspace.validate_session(data))
        data = copy.deepcopy(self.data)
        data["sources"] = [{"id": "S1", "kind": "paper", "title": "x", "url": "https://example.org",
                            "read_level": [], "checked_at": workspace.timestamp(), "takeaway": "x"}]
        item = candidate()
        item["source_ids"] = ["S1"]
        data["candidates"] = [item]
        self.assertTrue(workspace.validate_session(data))


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "user" / ".agents" / "skills" / "theme-advice-skill"

    def test_installed_skill_is_self_contained_and_excludes_development_files(self):
        destination, backup = installer.install(self.path)
        self.assertIsNone(backup)
        self.assertTrue((destination / "SKILL.md").is_file())
        self.assertTrue((destination / "scripts/workspace.py").is_file())
        self.assertFalse((destination / "tests").exists())
        isolated = module("workspace")
        isolated.SKILL_ROOT = destination
        student_work = Path(self.temporary.name) / "student-work"
        isolated.initialize(student_work)
        self.assertEqual(isolated.load_session(student_work)["schema_version"], "1.0")

    def test_reinstall_requires_update_and_preserves_existing_content(self):
        installer.install(self.path)
        marker = self.path / "custom-note.txt"
        marker.write_text("自分の変更", encoding="utf-8")
        with self.assertRaises(ValueError):
            installer.install(self.path)
        self.assertEqual(marker.read_text(), "自分の変更")

    def test_update_preserves_old_install_in_zip_and_does_not_copy_workspace(self):
        installer.install(self.path)
        (self.path / "custom-note.txt").write_text("以前の変更", encoding="utf-8")
        student_work = Path(self.temporary.name) / "graduation-theme"
        workspace.initialize(student_work)
        before = (student_work / "session.json").read_bytes()
        destination, backup = installer.install(self.path, update=True)
        self.assertTrue(backup.is_file())
        with zipfile.ZipFile(backup) as archive:
            self.assertEqual(archive.read("custom-note.txt").decode("utf-8"), "以前の変更")
        self.assertFalse((destination / "custom-note.txt").exists())
        self.assertEqual((student_work / "session.json").read_bytes(), before)
        self.assertEqual(len(list(self.path.parent.glob("*/SKILL.md"))), 1)

    def test_update_rollback_restores_old_install_if_final_rename_fails(self):
        installer.install(self.path)
        (self.path / "custom-note.txt").write_text("変更を保持", encoding="utf-8")
        original = Path.rename

        def fail_new_install(path, target):
            if path.name.startswith(".theme-advice-install-") and not path.name.endswith(".previous"):
                raise OSError("simulated install failure")
            return original(path, target)

        with patch.object(Path, "rename", fail_new_install):
            with self.assertRaises(OSError):
                installer.install(self.path, update=True)
        self.assertEqual((self.path / "custom-note.txt").read_text(), "変更を保持")

    def test_existing_non_skill_directory_is_never_replaced(self):
        self.path.mkdir(parents=True)
        (self.path / "note.txt").write_text("keep")
        with self.assertRaises(ValueError):
            installer.install(self.path, update=True)
        self.assertEqual((self.path / "note.txt").read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
