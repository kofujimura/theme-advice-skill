"""Checks the boundary between private working records and shared themes."""

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError, HTTPError

from test_scripts import module, candidate

workspace = module("workspace")
share = module("share")


class SharingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)
        workspace.initialize(self.path)
        data = workspace.load_session(self.path)
        data["student"].update(nickname="海", participant_id="private-student-id", own_words=["private quote"])
        data["candidates"] = [candidate()]
        data["selected_candidate_id"] = "C1"
        data["decisions"] = [{"at": workspace.timestamp(), "actor": "student", "action": "select", "candidate_id": "C1", "reason": "本人の選択", "student_quote": "private quote"}]
        workspace.write_json(self.path / "session.json", data)

    def test_exports_only_shared_fields_and_retains_id_on_unchanged_export(self):
        path, payload = share.export_theme(self.path)
        self.assertFalse(share.validate_public(payload))
        self.assertEqual(payload["author"], {"nickname": "海"})
        self.assertNotIn("student", payload)
        self.assertNotIn("readiness", payload["theme"])
        self.assertNotIn("student_feedback", payload["theme"])
        self.assertNotIn("private", path.read_text())
        before = path.read_bytes()
        self.assertEqual(share.export_theme(self.path)[1]["id"], payload["id"])
        self.assertEqual(path.read_bytes(), before)

    def test_revised_theme_gets_new_id_and_archives_previous_json(self):
        _, previous = share.export_theme(self.path)
        data = workspace.load_session(self.path); data["candidates"][0]["rq"] = "新しい問い"
        workspace.write_json(self.path / "session.json", data)
        _, revised = share.export_theme(self.path)
        self.assertNotEqual(previous["id"], revised["id"])
        archive = self.path / "shared-themes" / (previous["id"] + ".json")
        self.assertEqual(json.loads(archive.read_text()), previous)

    def test_local_source_never_exports_a_file_path(self):
        data = workspace.load_session(self.path)
        data["sources"] = [{"id": "S1", "kind": "other", "title": "ゼミ資料", "url": None, "file": "/private/student/file.md", "read_level": "full_text", "checked_at": workspace.timestamp(), "takeaway": "資料の内容"}]
        data["candidates"][0]["source_ids"] = ["S1"]
        workspace.write_json(self.path / "session.json", data)
        _, payload = share.export_theme(self.path)
        self.assertIsNone(payload["sources"][0]["url"])
        self.assertNotIn("file", payload["sources"][0])

    def test_nickname_and_student_selection_are_required_for_sharing(self):
        data = workspace.load_session(self.path); data["student"].pop("nickname")
        workspace.write_json(self.path / "session.json", data)
        self.assertFalse(workspace.validate_session(data))  # Backward-compatible session.
        with self.assertRaisesRegex(ValueError, "ニックネーム"):
            share.export_theme(self.path)
        data["student"]["nickname"] = "海"; data["selected_candidate_id"] = None
        workspace.write_json(self.path / "session.json", data)
        with self.assertRaisesRegex(ValueError, "本人が選"):
            share.export_theme(self.path)

    def test_schema_rejects_extra_private_fields_whitespace_names_and_fabricated_evidence(self):
        _, payload = share.export_theme(self.path)
        invalid = copy.deepcopy(payload); invalid["submit_token"] = "private"
        self.assertTrue(share.validate_public(invalid))
        invalid = copy.deepcopy(payload); invalid["author"]["nickname"] = "   "
        self.assertTrue(share.validate_public(invalid))
        invalid = copy.deepcopy(payload); invalid["theme"]["novelty"]["status"] = "search_scoped"
        self.assertTrue(share.validate_public(invalid))

    def test_only_https_or_explicit_local_http_is_allowed_and_redirects_are_disabled(self):
        self.assertEqual(share.site_url("https://test.example/"), "https://test.example")
        for value in ("http://test.example", "https://key@test.example", "https://test.example/?token=secret", "https://test.example/api/themes"):
            with self.assertRaises(ValueError): share.site_url(value)
        with self.assertRaises(ValueError): share.site_url("http://localhost:3210")
        self.assertEqual(share.site_url("http://localhost:3210", True), "http://localhost:3210")
        self.assertIsNone(share.NoRedirects().redirect_request(None, None, 302, "", {}, "https://elsewhere.example"))

    def test_send_records_unknown_on_network_failure_without_exposing_the_key(self):
        _, payload = share.export_theme(self.path)
        config = {"site_url": "https://test.example", "submit_token": "private-test-key-at-least-24-characters"}
        opener = unittest.mock.Mock(); opener.open.side_effect = URLError("offline")
        with patch.object(share, "configuration", return_value=config), patch.object(share, "build_opener", return_value=opener):
            with self.assertRaisesRegex(ValueError, "未確認"):
                share.submit(self.path)
        receipt = json.loads((self.path / "submission.json").read_text())
        self.assertEqual(receipt["status"], "unknown")
        self.assertEqual(receipt["id"], payload["id"])
        self.assertNotIn(config["submit_token"], (self.path / "submission.json").read_text())

    def test_config_persists_locally_with_private_permissions(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(share.main(["--workspace", str(self.path), "configure", "--site-url", "https://test.example"]), 0)
            self.assertEqual(share.configuration(self.path)["site_url"], "https://test.example")
            self.assertEqual((self.path / ".send-config.json").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
