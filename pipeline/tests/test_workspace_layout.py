from __future__ import annotations

import importlib
from pathlib import Path
import unittest


class WorkspaceLayoutTests(unittest.TestCase):
    def workspace_root(self) -> Path:
        parent = Path(__file__).resolve().parent.parent
        return parent.parent if parent.name == "pipeline" else parent

    def test_pipeline_namespace_and_public_entrypoints_exist(self):
        root = self.workspace_root()
        self.assertTrue((root / "pipeline").is_dir())

        for module in ("indices", "sectors", "gics", "macro", "context"):
            with self.subTest(module=module):
                importlib.import_module(f"pipeline.{module}")

    def test_only_target_visible_directories_remain(self):
        root = self.workspace_root()
        visible = {
            path.name
            for path in root.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        }

        self.assertEqual(visible, {"pipeline", "output"})


if __name__ == "__main__":
    unittest.main()
