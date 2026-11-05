"""Tests unitarios del nucleo del launcher (sin red ni GUI)."""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from azero import paths
from azero.auth import create_profile, offline_uuid, validate_username
from azero.install import PreparedGame
from azero.launch import build_command
from azero.libraries import maven_path
from azero.manifest import (_version_key, in_supported_range,
                            parse_version_key, resolve_version)
from azero.rules import expand_arguments, rules_allow
from azero.util import _Progress, extract_zip, human_size, write_json


class TestAuth(unittest.TestCase):
    def test_offline_uuid_is_deterministic_and_v3(self) -> None:
        first = offline_uuid("Notch")
        self.assertEqual(first, offline_uuid("Notch"))
        self.assertEqual(first, "b50ad385-829d-3141-a216-7e7d7539ba7f")
        # version 3 (tercer grupo empieza por 3) y variante IETF
        self.assertTrue(first.split("-")[2].startswith("3"))
        self.assertIn(first.split("-")[3][0], "89ab")

    def test_profile(self) -> None:
        profile = create_profile("Steve_")
        self.assertEqual(profile.name, "Steve_")
        self.assertEqual(profile.uuid, offline_uuid("Steve_"))
        self.assertEqual(profile.user_type, "legacy")

    def test_validate_username(self) -> None:
        self.assertIsNone(validate_username("Ab_12"))
        self.assertIsNotNone(validate_username(""))
        self.assertIsNotNone(validate_username("ab"))
        self.assertIsNotNone(validate_username("a" * 17))
        self.assertIsNotNone(validate_username("con espacio"))
        self.assertIsNotNone(validate_username("guion-bajo"))


class TestManifestKeys(unittest.TestCase):
    def test_version_key(self) -> None:
        self.assertEqual(_version_key("1.12.1"), (1, 12, 1))
        self.assertEqual(_version_key("1.8"), (1, 8, 0))
        self.assertIsNone(_version_key("23w13a"))
        self.assertIsNone(_version_key(""))

    def test_supported_range(self) -> None:
        self.assertTrue(in_supported_range("1.8.9"))
        self.assertTrue(in_supported_range("1.12.1"))
        self.assertTrue(in_supported_range("1.15.2"))
        self.assertFalse(in_supported_range("1.7.10"))
        self.assertFalse(in_supported_range("1.16.5"))
        self.assertEqual(parse_version_key("23w13a"), (0, 0, 0))


class TestRules(unittest.TestCase):
    def test_allow_disallow(self) -> None:
        windows_only = [{"action": "allow", "os": {"name": "windows"}}]
        self.assertTrue(rules_allow(windows_only))
        mac_only = [{"action": "allow", "os": {"name": "osx"}}]
        self.assertFalse(rules_allow(mac_only))
        mixed = [{"action": "allow"}, {"action": "disallow", "os": {"name": "osx"}}]
        # En Windows: allow coincide, disallow no -> permitido
        import azero.rules as rules_module
        original = rules_module.os_name
        try:
            rules_module.os_name = lambda: "windows"
            self.assertTrue(rules_allow(mixed))
            rules_module.os_name = lambda: "osx"
            self.assertFalse(rules_allow(mixed))
        finally:
            rules_module.os_name = original

    def test_expand_arguments(self) -> None:
        args = [
            "--foo",
            {"rules": [{"action": "allow"}], "value": ["--bar", "--baz"]},
            {"rules": [{"action": "disallow"}], "value": "--no"},
            {"rules": [{"action": "allow"}], "value": "--single"},
        ]
        self.assertEqual(expand_arguments(args),
                         ["--foo", "--bar", "--baz", "--single"])


class TestMavenPath(unittest.TestCase):
    def test_maven_path(self) -> None:
        self.assertEqual(
            maven_path("com.mojang:patchy:1.3.9"),
            "com/mojang/patchy/1.3.9/patchy-1.3.9.jar",
        )
        self.assertEqual(
            maven_path("optifine:Optifine:1.12.2_HD_U_G5"),
            "optifine/Optifine/1.12.2_HD_U_G5/Optifine-1.12.2_HD_U_G5.jar",
        )
        with self.assertRaises(ValueError):
            maven_path("sin-dos-puntos")


class TestResolveVersion(unittest.TestCase):
    def test_inheritance_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original = paths.VERSIONS_DIR
            paths.VERSIONS_DIR = Path(tmp)
            try:
                base = {
                    "id": "1.12.1",
                    "mainClass": "net.minecraft.client.main.Main",
                    "minecraftArguments": "--username ${auth_player_name}",
                    "assetIndex": {"id": "1.12"},
                    "libraries": [{"name": "a:b:1"}],
                    "javaVersion": {"majorVersion": 8},
                }
                child = {
                    "id": "1.12.1-OptiFine_HD_U_G5",
                    "inheritsFrom": "1.12.1",
                    "arguments": {"game": ["--tweakClass", "optifine.OptiFineTweaker"]},
                    "libraries": [{"name": "optifine:Optifine:1.12.2_HD_U_G5"}],
                }
                write_json(paths.version_json_path("1.12.1"), base)
                write_json(paths.version_json_path(child["id"]), child)

                merged = resolve_version(child["id"])
                self.assertEqual(merged["mainClass"], base["mainClass"])
                self.assertEqual(merged["minecraftArguments"],
                                 "--username ${auth_player_name}")
                self.assertEqual(merged["arguments"]["game"],
                                 ["--tweakClass", "optifine.OptiFineTweaker"])
                self.assertEqual(len(merged["libraries"]), 2)
                self.assertEqual(merged["assetIndex"]["id"], "1.12")
                self.assertEqual(merged["base_id"], "1.12.1")
            finally:
                paths.VERSIONS_DIR = original


class TestUtil(unittest.TestCase):
    def test_human_size(self) -> None:
        self.assertEqual(human_size(0), "0 B")
        self.assertEqual(human_size(512), "512 B")
        self.assertEqual(human_size(2048), "2.0 KB")
        self.assertEqual(human_size(5 * 1024 * 1024), "5.0 MB")

    def test_progress_rolls_back_on_retry(self) -> None:
        progress = _Progress()
        progress.add_total(100)
        progress.advance(50)
        progress.advance(-50)
        self.assertEqual(progress.done, 0)
        progress.advance(120)
        self.assertEqual(progress.done, 120)

    def test_extract_zip_blocks_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zip_path = root / "evil.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("ok/file.txt", "hola")
                archive.writestr("../escape.txt", "malo")
            dest = root / "dest"
            extract_zip(zip_path, dest)
            self.assertTrue((dest / "ok" / "file.txt").exists())
            self.assertFalse((root / "escape.txt").exists())
            self.assertFalse((dest / "escape.txt").exists())


class _FakeRuntime:
    java = Path("C:/java/bin/javaw.exe")


class TestBuildCommand(unittest.TestCase):
    def _prepared(self, version_json: dict) -> PreparedGame:
        return PreparedGame(
            version_id="test",
            base_id="base",
            main_class=version_json["mainClass"],
            classpath=[Path("C:/libs/a.jar"), Path("C:/libs/client.jar")],
            natives_dir=Path("C:/natives"),
            assets_dir=Path("C:/assets"),
            game_dir=Path("C:/game"),
            version_json=version_json,
            java_major=8,
            logging_path=None,
        )

    def _settings(self) -> SimpleNamespace:
        return SimpleNamespace(memory_mb=2048, extra_jvm_args="",
                               server="")

    def test_legacy_arguments_merges_optifine_tweaker(self) -> None:
        """Regresion: 1.12.x usa minecraftArguments; OptiFine anade
        arguments.game y ambos deben llegar a la linea de comandos."""
        version_json = {
            "mainClass": "net.minecraft.launchwrapper.Launch",
            "minecraftArguments": "--username ${auth_player_name} --gameDir ${game_directory}",
            "arguments": {"game": ["--tweakClass", "optifine.OptiFineTweaker"]},
            "assetIndex": {"id": "1.12"},
        }
        profile = create_profile("Steve")
        command = build_command(self._prepared(version_json), profile,
                                 self._settings(), _FakeRuntime())
        text = " ".join(command)
        self.assertIn("--username Steve", text)
        self.assertIn("--gameDir C:/game", text.replace("\\", "/"))
        self.assertIn("--tweakClass optifine.OptiFineTweaker", text)
        self.assertIn("-cp", command)
        self.assertIn("net.minecraft.launchwrapper.Launch", command)

    def test_modern_arguments_with_rules(self) -> None:
        version_json = {
            "mainClass": "net.minecraft.client.main.Main",
            "arguments": {
                "jvm": ["-Dfoo=bar",
                        # los manifiestos 1.13+ incluyen el classpath y la
                        # clase principal dentro de arguments.jvm
                        "-cp", "${classpath}", "${main_class}",
                        {"rules": [{"action": "allow"}],
                         "value": "-Dbaz=qux"}],
                "game": [{"rules": [{"action": "allow"}],
                          "value": ["--quickPlayPath", "${game_directory}"]}],
            },
            "assetIndex": {"id": "x"},
        }
        profile = create_profile("Alex")
        command = build_command(self._prepared(version_json), profile,
                                 self._settings(), _FakeRuntime())
        text = " ".join(command)
        self.assertIn("-Dfoo=bar", text)
        self.assertIn("-Dbaz=qux", text)
        self.assertIn("--quickPlayPath", text)
        # la clase principal solo debe aparecer una vez, tras -cp
        self.assertEqual(command.count("net.minecraft.client.main.Main"), 1)
        cp_index = command.index("-cp")
        self.assertEqual(command[cp_index + 2],
                         "net.minecraft.client.main.Main")


class TestJavaCompatibility(unittest.TestCase):
    def test_major_compatible(self) -> None:
        from azero.java import _major_compatible
        # 1.12.1 pide Java 8: acepta 8-16, rechaza 17+
        self.assertTrue(_major_compatible(8, 8))
        self.assertTrue(_major_compatible(11, 8))
        self.assertTrue(_major_compatible(16, 8))
        self.assertFalse(_major_compatible(17, 8))
        self.assertFalse(_major_compatible(21, 8))
        # Versiones nuevas: igual o mas reciente
        self.assertTrue(_major_compatible(21, 21))
        self.assertTrue(_major_compatible(21, 17))
        self.assertFalse(_major_compatible(8, 17))
        self.assertFalse(_major_compatible(16, 21))


if __name__ == "__main__":
    unittest.main()
