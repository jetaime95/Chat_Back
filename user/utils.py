from django.core.mail import send_mail

def send_verification_email(email, verification_code):
    """이메일 인증 번호 발송"""
    send_mail(
        '이메일 인증 번호',
        f'귀하의 인증번호는 {verification_code} 입니다. 10분 이내에 인증해주세요.',
        'your_email@example.com',
        [email],
        fail_silently=False,
    )