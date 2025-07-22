from .exception_handler import add_exception_handlers
from .keycloak import add_keycloak
from .webpush import add_webpush
from .modbus import add_modbus

def register_extensions(app):
    # Add new extensions imports below.
    add_exception_handlers(app)
    add_keycloak(app)
    add_webpush(app)
    add_modbus(app)