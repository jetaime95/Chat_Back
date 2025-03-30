import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_project.settings')

import django
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from middlewares.jwt_middleware import JWTWebSocketMiddleware
from user import routing as user_routing
from chat import routing as chat_routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # HTTP 요청 처리
    "websocket": AllowedHostsOriginValidator(
	JWTWebSocketMiddleware(
            URLRouter([
                # user 앱의 WebSocket 경로
                *user_routing.websocket_urlpatterns,
                # chat 앱의 WebSocket 경로
                *chat_routing.websocket_urlpatterns,
        	])
	)

    ),
})
