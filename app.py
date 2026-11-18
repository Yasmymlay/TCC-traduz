"""Ponto de entrada do TraduzEdu (usado pelo iniciar.bat).

A aplicação em si fica no pacote traduzedu/, organizado em MVC.
"""
import os

from traduzedu import create_app

app = create_app()


if __name__ == '__main__':
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '5001'))
    app.run(host=host, port=port, debug=False)
