"""Tests unitarios del nucleo del launcher (sin red ni GUI)."""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from azero import database, msauth, paths
from azero.auth import (OnlineProfile, create_profile, offline_uuid,
                        validate_username)
from azero.install import PreparedGame
from azero.launch import build_command
from azero.loaders import (_choose_stable, _neoforge_short_prefix,
                           loader_kind)
from azero.libraries import (build_library_plan, fix_authlib_session,
                             maven_path)
from azero.mods import _loader_of
from azero.manifest import (_version_key, in_supported_range,
                            parse_version_key, resolve_version,
                            version_family_label)
from azero.optifine import _parse_version_string, _split_edition_release
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
        self.assertEqual(_version_key("1.7.10"), (1, 7, 10))
        self.assertEqual(_version_key("26.3"), (26, 3, 0))
        self.assertEqual(_version_key("26.4-snapshot-7"), (26, 4, 0))
        self.assertEqual(_version_key("23w13a"), (23, 13, 1))
        self.assertEqual(_version_key("1.7.10-OptiFine_HD_U_I7"), (1, 7, 10))
        self.assertIsNone(_version_key(""))
        self.assertIsNone(_version_key("sin-version"))

    def test_supported_range(self) -> None:
        self.assertTrue(in_supported_range("1.7.2"))
        self.assertTrue(in_supported_range("1.7.10"))
        self.assertTrue(in_supported_range("1.8.9"))
        self.assertTrue(in_supported_range("1.12.1"))
        self.assertTrue(in_supported_range("1.15.2"))
        self.assertTrue(in_supported_range("1.21.5"))
        self.assertTrue(in_supported_range("26.3"))
        self.assertFalse(in_supported_range("1.6.4"))
        self.assertEqual(parse_version_key("23w13a"), (23, 13, 1))

    def test_family_label(self) -> None:
        self.assertEqual(version_family_label("1.12.2"), "1.12.x")
        self.assertEqual(version_family_label("1.7.10"), "1.7.x")
        self.assertEqual(version_family_label("1.21.5"), "1.21.x")
        self.assertEqual(version_family_label("26.3"), "26.x")
        self.assertEqual(version_family_label("26.4-snapshot-7"), "26.x")
        self.assertEqual(version_family_label("23w13a"), "23w")
        self.assertEqual(version_family_label("raro"), "Otras")


class TestOptiFineParsing(unittest.TestCase):
    def test_stable_edition(self) -> None:
        self.assertEqual(_split_edition_release("HD_U_G5"),
                         ("HD_U", "G5"))
        self.assertEqual(_parse_version_string("1.12.2_HD_U_G5"),
                         ("1.12.2", "HD_U", "G5"))

    def test_prerelease_edition(self) -> None:
        # Regresion: las ediciones _preN no parseaban y la instalacion
        # fallaba con "No se pudo determinar la version".
        self.assertEqual(_split_edition_release("HD_U_J1_pre9"),
                         ("HD_U", "J1_pre9"))
        self.assertEqual(_parse_version_string("1.21_HD_U_J1_pre9"),
                         ("1.21", "HD_U", "J1_pre9"))
        self.assertEqual(_parse_version_string("1.20.1_HD_U_I6"),
                         ("1.20.1", "HD_U", "I6"))

    def test_version_from_embedded_changelog(self) -> None:
        """Regresion: el nombre del archivo ya no importa; la version se
        lee de changelog.txt dentro del instalador."""
        from azero.optifine import inspect_installer
        with tempfile.TemporaryDirectory() as tmp:
            installer = Path(tmp) / "descarga (1).jar"
            with zipfile.ZipFile(installer, "w") as jar:
                jar.writestr("changelog.txt",
                             "OptiFine 1.21_HD_U_J1_pre9\n - fix\n")
                jar.writestr("notch/net/optifine/Config.class", b"x")
                jar.writestr("launchwrapper-of.txt", "2.3")
            info = inspect_installer(installer)
            self.assertEqual(info.mc_version, "1.21")
            self.assertEqual(info.edition_release, "HD_U_J1_pre9")
            self.assertEqual(info.profile_id,
                             "1.21-OptiFine_HD_U_J1_pre9")
            self.assertEqual(info.launchwrapper, "2.3")


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

    def test_clientreq_false_is_skipped(self) -> None:
        """Forge marca clientreq:false en libs solo de servidor."""
        version_json = {"libraries": [
            {"name": "a:b:1"},
            {"name": "c:d:2", "clientreq": False},
            {"name": "e:f:3", "clientreq": True},
        ]}
        plan = build_library_plan(version_json)
        names = [path.name for path in plan.classpath]
        self.assertEqual(len(names), 2)
        self.assertTrue(any("b-1.jar" in name for name in names))
        self.assertTrue(any("f-3.jar" in name for name in names))
        self.assertFalse(any("d-2.jar" in name for name in names))


class TestLoaderHelpers(unittest.TestCase):
    def test_loader_kind(self) -> None:
        self.assertEqual(loader_kind("fabric-loader-0.16.9-1.21.1"),
                         "fabric")
        self.assertEqual(loader_kind("neoforge-21.1.95"), "neoforge")
        self.assertEqual(loader_kind("1.21.1-forge-52.0.0"), "forge")
        self.assertEqual(loader_kind("1.12.2-OptiFine_HD_U_G5"),
                         "optifine")
        self.assertEqual(loader_kind("1.21.1"), "")

    def test_neoforge_short_prefix(self) -> None:
        self.assertEqual(_neoforge_short_prefix("1.21.1"), "21.1.")
        self.assertEqual(_neoforge_short_prefix("1.20.4"), "20.4.")
        self.assertEqual(_neoforge_short_prefix("26.1.2"), "26.1.")

    def test_choose_stable_skips_prereleases(self) -> None:
        self.assertEqual(
            _choose_stable(["0.1.0", "0.2.0-beta", "0.1.5"]), "0.1.5")
        self.assertEqual(_choose_stable(["1.0.0-beta"]), "1.0.0-beta")

    def test_mod_loader_detection(self) -> None:
        self.assertEqual(_loader_of(["fabric.mod.json", "x.class"]),
                         "fabric")
        self.assertEqual(
            _loader_of(["META-INF/neoforge.mods.toml"]), "neoforge")
        self.assertEqual(_loader_of(["META-INF/mods.toml"]), "forge")
        self.assertEqual(_loader_of(["mcmod.info"]), "forge")
        self.assertEqual(_loader_of(["com/example/Mod.class"]), "")


class TestAuthlibFix(unittest.TestCase):
    def _version_json(self, base_id: str, name: str =
                      "com.mojang:authlib:2.1.28") -> dict:
        return {"base_id": base_id, "libraries": [
            {"name": name, "downloads": {"artifact": {
                "path": "com/mojang/authlib/2.1.28/authlib-2.1.28.jar",
                "sha1": "ad54da276bf59983d02d5ed16fc14541354c71fd",
                "size": 76328}}}]}

    def test_swaps_authlib_on_1165(self) -> None:
        vj = self._version_json("1.16.5")
        self.assertTrue(fix_authlib_session(vj))
        lib = vj["libraries"][0]
        self.assertEqual(lib["name"], "com.mojang:authlib:2.3.31")
        self.assertIn("2.3.31", lib["downloads"]["artifact"]["path"])
        self.assertTrue(fix_authlib_session(vj))  # idempotente

    def test_ignores_other_versions(self) -> None:
        vj = self._version_json("1.17.1")
        self.assertFalse(fix_authlib_session(vj))
        self.assertEqual(vj["libraries"][0]["name"],
                         "com.mojang:authlib:2.1.28")


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

    def test_single_garbage_collector(self) -> None:
        """Regresion: 26.x trae -XX:+UseZGC en default-user-jvm; si el
        usuario elige otro GC no pueden quedar dos -XX:+Use*GC (la JVM
        aborta con 'Multiple garbage collectors selected')."""
        version_json = {
            "mainClass": "net.minecraft.client.main.Main",
            "arguments": {"default-user-jvm": [
                "-XX:+UseZGC", "-XX:+AlwaysPreTouch"]},
            "assetIndex": {"id": "x"},
        }
        profile = create_profile("Alex")

        settings = self._settings()
        settings.gc_preset = "serial"
        command = build_command(self._prepared(version_json), profile,
                                settings, _FakeRuntime())
        gcs = [a for a in command
               if a.startswith("-XX:") and "GC" in a]
        self.assertEqual(gcs, ["-XX:+UseSerialGC"])
        self.assertIn("-XX:+AlwaysPreTouch", command)

        settings.gc_preset = "auto"
        command = build_command(self._prepared(version_json), profile,
                                settings, _FakeRuntime())
        gcs = [a for a in command
               if a.startswith("-XX:") and "GC" in a]
        self.assertEqual(gcs, ["-XX:+UseZGC"])

    def test_extra_jvm_gc_overrides_all(self) -> None:
        """Regresion: un -XX:+Use*GC en extra_jvm_args tambien debe ganar
        al preset y al manifiesto, o la JVM aborta con 'Multiple garbage
        collectors selected'."""
        version_json = {
            "mainClass": "net.minecraft.client.main.Main",
            "arguments": {"default-user-jvm": ["-XX:+UseZGC"]},
            "assetIndex": {"id": "x"},
        }
        profile = create_profile("Alex")

        settings = self._settings()
        settings.gc_preset = "serial"
        settings.extra_jvm_args = "-XX:+UseG1GC -Dfoo=bar"
        command = build_command(self._prepared(version_json), profile,
                                settings, _FakeRuntime())
        gcs = [a for a in command
               if a.startswith("-XX:") and "GC" in a]
        self.assertEqual(gcs, ["-XX:+UseG1GC"])
        self.assertIn("-Dfoo=bar", command)

        # Sin GC en extra_jvm_args el preset sigue ganando al manifiesto.
        settings.extra_jvm_args = "-Dfoo=bar"
        command = build_command(self._prepared(version_json), profile,
                                settings, _FakeRuntime())
        gcs = [a for a in command
               if a.startswith("-XX:") and "GC" in a]
        self.assertEqual(gcs, ["-XX:+UseSerialGC"])


class TestMcScan(unittest.TestCase):
    def test_detect_mc_root_variants(self) -> None:
        from azero import mcscan
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mc = root / "cualquier-nombre" / ".minecraft"
            versions = mc / "versions" / "1.12.2"
            versions.mkdir(parents=True)
            (versions / "1.12.2.json").write_text("{}", encoding="utf-8")

            # 1) la raiz .minecraft directamente
            self.assertEqual(mcscan.detect_mc_root(mc), mc.resolve())
            # 2) su subcarpeta versions/ (o cualquier nombre)
            self.assertEqual(
                mcscan.detect_mc_root(mc / "versions"), mc.resolve())
            # 3) una carpeta contenedora (un nivel arriba de .minecraft)
            self.assertEqual(
                mcscan.detect_mc_root(mc.parent), mc.resolve())
            # 4) la carpeta versions renombrada
            stray = root / "juegos" / "mc_perfiles"
            (stray / "1.8.9").mkdir(parents=True)
            (stray / "1.8.9" / "1.8.9.json").write_text(
                "{}", encoding="utf-8")
            self.assertEqual(
                mcscan.detect_mc_root(stray), stray.resolve().parent)
            # 5) carpeta sin Minecraft -> None
            empty = root / "vacio"
            empty.mkdir()
            self.assertIsNone(mcscan.detect_mc_root(empty))


class TestAssetIntegrity(unittest.TestCase):
    def test_corrupt_objects_detects_bad_sha1(self) -> None:
        """Regresion: un objeto de assets corrupto con tamano correcto
        no se detectaba nunca; con internet debe repararse."""
        import hashlib
        from azero import assets
        with tempfile.TemporaryDirectory() as tmp:
            old_assets = paths.ASSETS_DIR
            paths.ASSETS_DIR = Path(tmp)
            try:
                good = hashlib.sha1(b"ok").hexdigest()
                bad = hashlib.sha1(b"roto").hexdigest()
                objects = paths.ASSETS_DIR / "objects"
                (objects / good[:2]).mkdir(parents=True)
                (objects / bad[:2]).mkdir(parents=True)
                (objects / good[:2] / good).write_bytes(b"ok")
                (objects / bad[:2] / bad).write_bytes(b"contenido malo")
                index = {"objects": {
                    "a": {"hash": good, "size": 2},
                    "b": {"hash": bad, "size": 13},
                    "c": {"hash": "f" * 40, "size": 5},  # ausente: no es corrupto
                }}
                corrupt = assets.corrupt_objects(index)
                self.assertEqual([p.name for p in corrupt], [bad])
            finally:
                paths.ASSETS_DIR = old_assets


class TestSettingsSanitize(unittest.TestCase):
    def test_invalid_types_are_dropped(self) -> None:
        from azero.settings import _sanitize
        clean = _sanitize({
            "memory_mb": "4096",          # str numerica -> int
            "cpu_cores": "abc",           # no numerica -> fuera
            "gpu_accel": "false",         # str bool -> False
            "auto_close": True,
            "username": 123,              # tipo erroneo -> fuera
            "unknown_key": "x",           # ya filtrado antes, por si acaso
        })
        self.assertEqual(clean["memory_mb"], 4096)
        self.assertNotIn("cpu_cores", clean)
        self.assertIs(clean["gpu_accel"], False)
        self.assertIs(clean["auto_close"], True)
        self.assertNotIn("username", clean)
        self.assertNotIn("unknown_key", clean)

    def test_load_clamps_out_of_range_values(self) -> None:
        """Regresion: un settings.json editado a mano con memory_mb
        desbordado o enums invalidos rompia la JVM o el selector."""
        from azero.settings import Settings
        with tempfile.TemporaryDirectory() as tmp:
            old_dir = paths.DATA_DIR
            old_file = paths.SETTINGS_FILE
            paths.DATA_DIR = Path(tmp)
            paths.SETTINGS_FILE = paths.DATA_DIR / "settings.json"
            try:
                paths.SETTINGS_FILE.write_text(
                    '{"memory_mb": 999999, "game_priority": "turbo",'
                    ' "gc_preset": "bogus", "cpu_cores": -3,'
                    ' "hw_defaults_applied": true}',
                    encoding="utf-8")
                settings = Settings.load()
                self.assertEqual(settings.memory_mb, 16384)
                self.assertEqual(settings.game_priority, "normal")
                self.assertEqual(settings.gc_preset, "auto")
                self.assertEqual(settings.cpu_cores, 0)
            finally:
                paths.DATA_DIR = old_dir
                paths.SETTINGS_FILE = old_file


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


class TestOnlineProfile(unittest.TestCase):
    def test_uuid_dashed(self) -> None:
        profile = OnlineProfile(name="Alex", uuid="a" * 32,
                                access_token="tok")
        self.assertEqual(profile.uuid_dashed,
                         "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        self.assertEqual(profile.user_type, "msa")


class TestResolveProfile(unittest.TestCase):
    def test_offline_profile(self) -> None:
        settings = SimpleNamespace(username="Steve", active_account="")
        profile = msauth.resolve_profile(settings)
        self.assertEqual(profile.name, "Steve")
        self.assertEqual(profile.uuid, offline_uuid("Steve"))
        self.assertEqual(profile.user_type, "legacy")

    def test_invalid_offline_name(self) -> None:
        settings = SimpleNamespace(username="no vale!", active_account="")
        with self.assertRaises(msauth.MsaError):
            msauth.resolve_profile(settings)

    def test_missing_ms_account(self) -> None:
        settings = SimpleNamespace(username="Steve",
                                   active_account="ms:deadbeef")
        with self.assertRaises(msauth.MsaError):
            msauth.resolve_profile(settings)


class TestDatabase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._old = paths.DATA_DIR
        paths.DATA_DIR = Path(self._tmp.name)
        paths.SETTINGS_FILE = paths.DATA_DIR / "settings.json"
        database.init_db()

    def tearDown(self) -> None:
        paths.DATA_DIR = self._old
        self._tmp.cleanup()

    def test_downloads_and_sessions_roundtrip(self) -> None:
        database.log_download("version", "Cliente 1.15.2",
                              version_id="1.15.2", size_bytes=100)
        sid = database.session_start("Steve", "u", "1.15.2", "offline",
                                     pid=123)
        database.session_end(sid, exit_code=0)
        downloads = database.list_downloads()
        sessions = database.list_sessions()
        self.assertEqual(len(downloads), 1)
        self.assertEqual(downloads[0]["label"], "Cliente 1.15.2")
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["exit_code"], 0)
        self.assertIsNotNone(sessions[0]["ended"])

    def test_accounts_roundtrip(self) -> None:
        database.save_account("a" * 32, "TestMC", "refresh")
        database.save_account("a" * 32, "TestMC2", "refresh2")
        accounts = database.list_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["mc_name"], "TestMC2")
        database.delete_account("a" * 32)
        self.assertEqual(database.list_accounts(), [])


if __name__ == "__main__":
    unittest.main()
