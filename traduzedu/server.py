"""Inicialização do servidor local."""
import socket
import sys


def port_in_use(host, port):
    """Indica se outro processo já ocupa a porta.

    No Windows, o servidor do Flask usa SO_REUSEADDR, o que permite que dois
    servidores escutem a mesma porta. As requisições então podem cair num
    servidor antigo travado. A verificação com SO_EXCLUSIVEADDRUSE evita isso.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return True
    return False


def run(app, host, port):
    if port_in_use(host, port):
        print(
            f'A porta {port} já está em uso por outro processo, provavelmente uma '
            'janela antiga do Tradutor de Aulas. Feche essa janela (ou encerre o '
            'processo python) e execute iniciar.bat novamente.',
            file=sys.stderr,
        )
        sys.exit(1)
    app.run(host=host, port=port, debug=False, threaded=True)
