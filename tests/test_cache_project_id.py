import unittest
import os
import tempfile
import shutil
from src.utils.path_manager import normalize_project_name, get_project_id

class TestCacheProjectId(unittest.TestCase):
    def test_normalize_project_name(self):
        self.assertEqual(normalize_project_name("Lust Village 0.1"), "Lust Village")
        self.assertEqual(normalize_project_name("Lust Village v0.2.3-pc"), "Lust Village")
        self.assertEqual(normalize_project_name("Lust_Village_v1.0"), "Lust_Village")
        self.assertEqual(normalize_project_name("Lust Village (1)"), "Lust Village")
        self.assertEqual(normalize_project_name("Lust Village - Win"), "Lust Village")
        self.assertEqual(normalize_project_name("Lust Village Beta"), "Lust Village")
        self.assertEqual(normalize_project_name("Lust Village-pc-win"), "Lust Village")
        self.assertEqual(normalize_project_name("Lust Village 2026.04"), "Lust Village")
        self.assertEqual(normalize_project_name("Lust Village"), "Lust Village")
        self.assertEqual(normalize_project_name("LustVillage"), "LustVillage")
        self.assertEqual(normalize_project_name(""), "")

    def test_get_project_id_fallback_to_folder(self):
        # Fallback case: no options.rpy and no exe
        self.assertEqual(get_project_id("/Games/Lust Village 0.1"), "Lust Village")
        self.assertEqual(get_project_id("/Games/Lust Village v0.2.3-pc"), "Lust Village")

    def test_get_project_id_from_options_rpy(self):
        temp_dir = tempfile.mkdtemp()
        try:
            game_dir = os.path.join(temp_dir, "game")
            os.makedirs(game_dir, exist_ok=True)
            
            # 1. Test config.save_directory
            options_path = os.path.join(game_dir, "options.rpy")
            with open(options_path, "w", encoding="utf-8") as f:
                f.write('define config.save_directory = "LustVillage_Save_123"\n')
                
            project_id = get_project_id(temp_dir)
            self.assertEqual(project_id, "renpy_LustVillage_Save_123")
            
            # 2. Test config.name fallback if save_directory is empty
            with open(options_path, "w", encoding="utf-8") as f:
                f.write('define config.name = _("Lust Village 0.2")\n')
                
            project_id = get_project_id(temp_dir)
            self.assertEqual(project_id, "renpy_Lust Village")
        finally:
            shutil.rmtree(temp_dir)

    def test_get_project_id_from_exe(self):
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a mock exe file
            exe_path = os.path.join(temp_dir, "LustVillageGame.exe")
            with open(exe_path, "w") as f:
                f.write("")
                
            project_id = get_project_id(temp_dir, exe_path)
            self.assertEqual(project_id, "LustVillageGame")
            
            # Test strategy 3: scan folder for exe
            project_id = get_project_id(temp_dir)
            self.assertEqual(project_id, "LustVillageGame")
        finally:
            shutil.rmtree(temp_dir)

if __name__ == '__main__':
    unittest.main()
