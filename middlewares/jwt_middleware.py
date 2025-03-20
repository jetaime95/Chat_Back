from urllib.parse import parse_qs
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import AnonymousUser
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()

class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # URL에서 query_string을 받아옴
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        
        # token 파라미터 추출
        token = query_params.get("token", [None])[0]

        # JWT Token이 Bearer 형식일 경우, 'Bearer ' 부분을 제거하고 실제 토큰만 사용
        if token and token.startswith("Bearer "):
            token = token[7:]  # 'Bearer ' 길이는 7이므로 그만큼 자르기

        print(f"JWT Middleware: Token received - {token}")

        if token:
            try:
                # AccessToken 검증
                validated_token = AccessToken(token)
                user_id = validated_token["user_id"]

                # 데이터베이스에서 사용자 조회
                user = await sync_to_async(User.objects.get)(id=user_id)
                scope["user"] = user

                print(f"JWT Middleware: User set to - {scope['user']}")
            except Exception as e:
                print(f"JWT Error: {e}")
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()

        # WebSocket 연결 처리
        return await self.inner(scope, receive, send)
    
class JWTAuthMiddlewareStack:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # JWT 인증 처리
        return await JWTAuthMiddleware(self.inner).__call__(scope, receive, send)