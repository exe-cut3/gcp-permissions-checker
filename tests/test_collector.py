import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import commit_helper  # noqa: E402
import get_permissions  # noqa: E402


class ToRecord(unittest.TestCase):
    def test_missing_stage_means_alpha(self):
        record = get_permissions.to_record({"name": "x.y.get"})
        self.assertEqual(record["stage"], "ALPHA")
        self.assertEqual(record["customRolesSupportLevel"], "SUPPORTED")

    def test_reported_values_are_kept(self):
        permission = {
            "name": "x.y.get",
            "title": "Get Y",
            "description": "Reads a Y",
            "stage": "GA",
            "customRolesSupportLevel": "TESTING",
            "primaryPermission": "x.z.get",
        }
        self.assertEqual(get_permissions.to_record(permission), permission)

    def test_project_specific_and_empty_fields_are_dropped(self):
        record = get_permissions.to_record(
            {"name": "x.y.get", "description": "", "apiDisabled": True, "stage": "BETA"}
        )
        self.assertNotIn("apiDisabled", record)
        self.assertNotIn("description", record)
        self.assertEqual(record["stage"], "BETA")


class WriteOutputs(unittest.TestCase):
    def test_both_files_describe_the_same_sorted_catalog(self):
        records = {
            name: get_permissions.to_record({"name": name, "stage": "GA"})
            for name in ("b.x.get", "a.x.get")
        }
        with tempfile.TemporaryDirectory() as tmp:
            txt = os.path.join(tmp, "permissions.txt")
            meta = os.path.join(tmp, "permissions_metadata.jsonl")
            get_permissions.write_outputs(records, txt, meta)

            names = Path(txt).read_text(encoding="utf-8").splitlines()
            lines = Path(meta).read_text(encoding="utf-8").splitlines()
            self.assertEqual(names, ["a.x.get", "b.x.get"])
            self.assertEqual([json.loads(line)["name"] for line in lines], names)
            self.assertEqual(sorted(os.listdir(tmp)), ["permissions.txt", "permissions_metadata.jsonl"])


class DescribeMetadataChanges(unittest.TestCase):
    BETA = {"name": "a.x.get", "stage": "BETA"}
    GA = {"name": "a.x.get", "stage": "GA"}

    def test_first_snapshot_is_reported_once(self):
        self.assertEqual(
            commit_helper.describe_metadata_changes({"a.x.get": self.GA}, {}),
            "metadata snapshot of 1 permission",
        )

    def test_stage_promotion_is_reported(self):
        self.assertEqual(
            commit_helper.describe_metadata_changes({"a.x.get": self.GA}, {"a.x.get": self.BETA}),
            "1 metadata change (1 stage)",
        )

    def test_title_edit_is_not_counted_as_stage(self):
        retitled = dict(self.GA, title="New title")
        self.assertEqual(
            commit_helper.describe_metadata_changes({"a.x.get": retitled}, {"a.x.get": self.GA}),
            "1 metadata change",
        )

    def test_unchanged_metadata_is_silent(self):
        self.assertEqual(
            commit_helper.describe_metadata_changes({"a.x.get": self.GA}, {"a.x.get": self.GA}), ""
        )

    def test_new_permissions_are_left_to_permissions_txt(self):
        current = {"a.x.get": self.GA, "b.x.get": {"name": "b.x.get", "stage": "GA"}}
        self.assertEqual(commit_helper.describe_metadata_changes(current, {"a.x.get": self.GA}), "")


if __name__ == "__main__":
    unittest.main()
