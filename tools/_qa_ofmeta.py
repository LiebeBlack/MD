import sys, zipfile, json, re
sys.path.insert(0, '.')
from pathlib import Path

jar_path = Path(r"C:\Users\Admin\AppData\Local\Temp\OptiFine_1.20.1_HD_U_I6.jar")
with zipfile.ZipFile(jar_path) as jar:
    names = jar.namelist()
    # archivos de texto/props en raiz o meta
    meta = [n for n in names if ("/" not in n.strip("/") or n.count("/") <= 2)
            and re.search(r"\.(txt|properties|json|mf|xml|version)$|version|build|changelog|readme", n, re.I)]
    print("meta candidates:")
    for n in meta[:50]:
        print("  ", n)
    # manifest completo
    print("--- MANIFEST ---")
    print(jar.read("META-INF/MANIFEST.MF").decode("utf-8", "ignore"))
    # archivos .properties
    for n in names:
        if n.endswith(".properties"):
            print("---", n)
            print(jar.read(n).decode("utf-8", "ignore")[:500])
    # txt en raiz
    for n in names:
        if n.endswith(".txt") and n.count("/") <= 1:
            print("---", n)
            print(jar.read(n).decode("utf-8", "ignore")[:300])
