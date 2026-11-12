# Flashdeck — сборка в один исполняемый файл: pyinstaller flashdeck.spec
# by Benovich · https://github.com/Denchikper/flashdeck

datas = [
    ("flashdeck/ui/forms/*.ui", "flashdeck/ui/forms"),
    ("assets/icon.png", "assets"),
    ("assets/sample_english.csv", "assets"),
]

# Модули Qt, которые приложению не нужны, — чтобы exe был меньше
excludes = [
    "tkinter",
    "PyQt6.QtNetwork",
    "PyQt6.QtQml",
    "PyQt6.QtQuick",
    "PyQt6.QtMultimedia",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtPdf",
    "PyQt6.QtBluetooth",
    "PyQt6.QtSql",
]

a = Analysis(
    ["main.py"],
    datas=datas,
    excludes=excludes,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="Flashdeck",
    icon="assets/icon.ico",
    console=False,
    upx=False,
)
