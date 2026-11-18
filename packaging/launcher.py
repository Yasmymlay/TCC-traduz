"""Inicializador do Tradutor de Aulas para a versão instalável (.exe).

Abre uma janela pequena, sobe o servidor Flask numa porta livre e abre o
navegador. Fechar a janela encerra o programa. Os modelos de tradução Argos
e o Tesseract OCR vêm dentro do pacote, então nada precisa ser instalado à
parte.
"""
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

APP_NAME = 'Tradutor de Aulas'


def bundle_dir():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))


def configure_environment(base):
    """Aponta o sistema para os recursos que vêm dentro do pacote."""
    models = base / 'argos-packages'
    if models.is_dir():
        os.environ.setdefault('ARGOS_TRANSLATE_PACKAGE_DIR', str(models))
    tesseract = base / 'tesseract' / 'tesseract.exe'
    if tesseract.is_file():
        os.environ.setdefault('TESSERACT_CMD', str(tesseract))
        os.environ.setdefault('TESSDATA_PREFIX', str(tesseract.parent / 'tessdata'))
    # O LibreTranslate não vem no instalador; sem ele o sistema não perde
    # 2 segundos tentando conectar em cada tradução.
    os.environ.setdefault('TRANSLATION_PROVIDERS', 'argos,deepl')
    os.environ.setdefault('ARGOS_STANZA_AVAILABLE', 'false')


def free_port(preferred=5001):
    from traduzedu.server import port_in_use
    if not port_in_use('127.0.0.1', preferred):
        return preferred
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def start_server(port):
    from werkzeug.serving import make_server
    from traduzedu import create_app

    server = make_server('127.0.0.1', port, create_app(), threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def show_window(url, server):
    import tkinter as tk

    root = tk.Tk()
    root.title(APP_NAME)
    root.resizable(False, False)
    icon = bundle_dir() / 'icone.ico'
    if icon.is_file():
        try:
            root.iconbitmap(str(icon))
        except tk.TclError:
            pass
    frame = tk.Frame(root, padx=24, pady=18)
    frame.pack()
    tk.Label(frame, text=f'{APP_NAME} está aberto', font=('Segoe UI', 13, 'bold')).pack(anchor='w')
    tk.Label(
        frame,
        text='O sistema abre no seu navegador.\nFeche esta janela quando terminar de usar.',
        font=('Segoe UI', 10), justify='left',
    ).pack(anchor='w', pady=(6, 14))
    buttons = tk.Frame(frame)
    buttons.pack(fill='x')

    def close():
        server.shutdown()
        root.destroy()

    tk.Button(buttons, text='Abrir no navegador', width=20,
              command=lambda: webbrowser.open(url)).pack(side='left')
    tk.Button(buttons, text='Fechar', width=12, command=close).pack(side='right')
    root.protocol('WM_DELETE_WINDOW', close)
    root.after(600, lambda: webbrowser.open(url))
    root.mainloop()


def main():
    base = bundle_dir()
    configure_environment(base)
    # Sem console no .exe, a saída vai para um arquivo de log do usuário.
    if getattr(sys, 'frozen', False):
        log_dir = Path(os.getenv('LOCALAPPDATA', Path.home())) / 'TradutorDeAulas'
        log_dir.mkdir(parents=True, exist_ok=True)
        log = open(log_dir / 'servidor.log', 'a', encoding='utf-8', buffering=1)
        sys.stdout = sys.stderr = log
    port = free_port()
    server = start_server(port)
    show_window(f'http://127.0.0.1:{port}', server)


if __name__ == '__main__':
    main()
