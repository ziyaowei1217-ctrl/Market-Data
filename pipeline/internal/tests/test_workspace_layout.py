from __future__ import annotations

import importlib
from pathlib import Path
import unittest


class WorkspaceLayoutTests(unittest.TestCase):
    def workspace_root(self) -> Path:
        pipeline_root = next(
            parent
            for parent in Path(__file__).resolve().parents
            if parent.name == "pipeline"
        )
        return pipeline_root.parent

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

    def test_pipeline_keeps_one_internal_engineering_directory(self):
        pipeline_root = self.workspace_root() / "pipeline"
        visible_directories = {
            path.name
            for path in pipeline_root.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
            and path.name != "__pycache__"
        }
        visible_files = {
            path.name
            for path in pipeline_root.iterdir()
            if path.is_file() and not path.name.startswith(".")
        }

        self.assertEqual(visible_directories, {"internal"})
        self.assertEqual(
            visible_files,
            {
                "__init__.py",
                "config.json",
                "context.py",
                "gics.py",
                "indices.py",
                "macro.py",
                "refresh.py",
                "requirements.txt",
                "sectors.py",
            },
        )

    def test_internal_implementation_imports_from_one_namespace(self):
        for module in (
            "pipeline.internal.capital_weekly.weekly_release",
            "pipeline.internal.scripts.fetch_equity_indices",
            "pipeline.internal.tests.test_pipeline_config",
        ):
            with self.subTest(module=module):
                importlib.import_module(module)


if __name__ == "__main__":
    unittest.main()
