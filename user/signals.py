from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
from django.conf import settings

@receiver(user_logged_out)
def set_user_offline(sender, request, user, **kwargs):
    if user is not None:  # 로그아웃 시 익명 사용자를 방지
        user.is_online = False
        user.save()
        print(f"User {user.username}는 오프라인입니다.")