"""Camada Controller: recebe as requisições HTTP e coordena models e services."""
from .download_controller import download_bp
from .pages_controller import pages_bp
from .resources_controller import resources_bp
from .translation_controller import translation_bp

BLUEPRINTS = (pages_bp, translation_bp, download_bp, resources_bp)


def register_controllers(app):
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
