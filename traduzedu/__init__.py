"""TraduzEdu - plataforma de tradução de materiais educacionais.

Organização em MVC:
    models/       estrutura do documento, idiomas e regras de texto
    views/        templates HTML e arquivos estáticos (CSS, JS, exemplos)
    controllers/  rotas Flask (Blueprints) que ligam a View aos serviços
    services/     extração, OCR, tradução e exportação de arquivos
"""
from flask import Flask, jsonify

from .config import STATIC_DIR, TEMPLATES_DIR, Config
from .controllers import register_controllers


def create_app(config_object=Config):
    app = Flask(
        __name__,
        template_folder=str(TEMPLATES_DIR),
        static_folder=str(STATIC_DIR),
        static_url_path='/static',
    )
    app.config.from_object(config_object)
    register_controllers(app)

    @app.errorhandler(413)
    def request_entity_too_large(_error):
        return jsonify({
            'error': 'O arquivo ou conteúdo enviado excede o limite de 10 MB.'
        }), 413

    return app
