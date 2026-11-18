# Empacotamento do Tradutor de Aulas com PyInstaller (pasta única, sem console).
# Use packaging\build.ps1, que prepara os recursos e chama este arquivo.
import os
from pathlib import Path

ROOT = Path(SPECPATH).parent
RES = Path(os.environ['TRADUTOR_RESOURCES'])

datas = [
    (str(ROOT / 'traduzedu' / 'views'), 'traduzedu/views'),
    (str(ROOT / 'traduzedu' / 'data'), 'traduzedu/data'),
    (str(RES / 'argos-packages'), 'argos-packages'),
    (str(RES / 'tesseract'), 'tesseract'),
    (str(ROOT / 'packaging' / 'icone.ico'), '.'),
]

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
for package in ('argostranslate', 'minisbd', 'sacremoses', 'reportlab'):
    datas += collect_data_files(package)
binaries = collect_dynamic_libs('ctranslate2') + collect_dynamic_libs('onnxruntime')

a = Analysis(
    [str(ROOT / 'packaging' / 'launcher.py')],
    pathex=[str(ROOT / 'packaging' / 'stubs'), str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=['traduzedu', 'stanza', 'sentencepiece', 'ctranslate2'],
    excludes=['torch', 'spacy', 'thinc', 'stanza.models', 'matplotlib', 'IPython',
              'pandas', 'scipy', 'tensorflow', 'pytest'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='TradutorDeAulas',
    console=False,
    icon=str(ROOT / 'packaging' / 'icone.ico'),
)
coll = COLLECT(exe, a.binaries, a.datas, name='TradutorDeAulas')
