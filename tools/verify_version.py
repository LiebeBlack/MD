"""Verificacion QA de una version de Minecraft sin descargar el juego.

Uso:
    python tools/verify_version.py 1.12.1

Comprueba: manifiesto -> version.json -> herencia -> plan de librerias ->
nativos -> indice de assets -> line de comandos -> disponibilidad HTTP de
todas las URLs de descarga (HEAD).
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from azero import manifest, paths
from azero.assets import asset_tasks, ensure_asset_index
from azero.install import TaskContext, ensure_profile_chain
from azero.launch import build_command
from azero.libraries import build_library_plan
from azero.settings import Settings
from azero.auth import create_profile


def head_ok(url: str) -> bool:
    request = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "AZeroCraft-QA/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status == 200
    except Exception:
        return False


def main() -> int:
    version_id = sys.argv[1] if len(sys.argv) > 1 else "1.12.1"
    ctx = TaskContext()

    print(f"== Manifiesto oficial ==")
    data = manifest.fetch_manifest()
    print(f"versiones en manifiesto: {len(data.get('versions', []))}")

    print(f"\n== Perfil {version_id} ==")
    ensure_profile_chain(version_id, data)
    cached = manifest.load_version_profile(version_id) or {}
    print(f"mainClass: {cached.get('mainClass')}")
    print(f"inheritsFrom: {cached.get('inheritsFrom')}")

    print(f"\n== Resolucion con herencia ==")
    resolved = manifest.resolve_version(version_id)
    print(f"base_id: {resolved['base_id']}")
    print(f"mainClass: {resolved['mainClass']}")
    print(f"javaVersion: {resolved.get('javaVersion')}")
    print(f"libraries: {len(resolved['libraries'])}")

    print(f"\n== Plan de librerias ==")
    plan = build_library_plan(resolved)
    print(f"descargas: {len(plan.downloads)}")
    print(f"classpath: {len(plan.classpath)}")
    print(f"nativos: {len(plan.natives)}")
    for jar, _ in plan.natives:
        print(f"  nativo: {jar.name}")

    print(f"\n== Assets ==")
    index = ensure_asset_index(resolved["assetIndex"])
    tasks, total = asset_tasks(index)
    print(f"indice {resolved['assetIndex']['id']}: {len(tasks)} objetos, "
          f"{total / 1024 / 1024:.0f} MiB")

    print(f"\n== Linea de comandos ==")
    settings = Settings(username="QA_Tester", version=version_id,
                        memory_mb=2048)
    prepared = type("P", (), {})()
    prepared.version_id = version_id
    prepared.base_id = resolved["base_id"]
    prepared.main_class = resolved["mainClass"]
    prepared.classpath = [paths.version_jar_path(resolved["base_id"]),
                          *plan.classpath]
    prepared.natives_dir = paths.natives_dir(version_id)
    prepared.assets_dir = paths.ASSETS_DIR
    prepared.game_dir = paths.MC_DIR
    prepared.version_json = resolved
    prepared.java_major = manifest.preferred_java_major(
        version_id, resolved.get("base_id") or "")
    prepared.logging_path = None

    class _Runtime:
        java = Path("java")

    command = build_command(prepared, create_profile("QA_Tester"), settings,
                            _Runtime())
    print(" ".join(command)[:600])
    print("...")

    print(f"\n== Comprobacion HTTP (HEAD) ==")
    urls = [task.url for task in plan.downloads]
    client = (resolved.get("downloads") or {}).get("client")
    if client:
        urls.append(client["url"])
    urls.append(resolved["assetIndex"]["url"])
    bad = [url for url in urls if not head_ok(url)]
    print(f"{len(urls)} URLs comprobadas, {len(bad)} fallidas")
    for url in bad[:10]:
        print(f"  FALLO: {url}")

    print(f"\n== Resultado ==")
    if bad:
        print("FALLO: hay URLs inaccesibles")
        return 1
    print("OK: version resuelta, plan completo y todas las URLs accesibles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
