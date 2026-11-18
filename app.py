"""Ponto de entrada do TraduzEdu (usado pelo iniciar.bat).

A aplicação em si fica no pacote traduzedu/, organizado em MVC.
"""
import os

from traduzedu import create_app
from traduzedu.server import run

app = create_app()


if __name__ == '__main__':
    run(app, os.getenv('HOST', '127.0.0.1'), int(os.getenv('PORT', '5001')))
