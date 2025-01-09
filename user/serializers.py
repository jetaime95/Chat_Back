from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from user.models import User, EmailVerification
from django.core.mail import send_mail
import random

# 이메일 요청
class EmailVerificationSerializer(serializers.Serializer):
    # 이메일 필드 정의의
    email = serializers.EmailField()
    # 이메일 인증 레코드 생성성
    def create(self, validated_data):
        email = validated_data['email']
        # 기존 인증 레코드 삭제
        EmailVerification.objects.filter(email=email).delete()
        # 6자리 인증번호 생성
        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        # 새 인증 레코드 생성
        email_verification = EmailVerification.objects.create(
            email=email,
            verification_code=verification_code
        )
        # 인증번호 이메일 발송
        send_mail(
            '이메일 인증 번호',
            f'귀하의 인증번호는 {verification_code} 입니다. 10분 이내에 인증해주세요.',
            'your_email@example.com',
            [email],
            fail_silently=False,
        )
        # 생성된 인증 레코드 반환
        return email_verification

# 인증번호 유효성 검사
class VerifyCodeSerializer(serializers.Serializer):
    # 이메일과 인증번호 필드를 정의
    email = serializers.EmailField()
    verification_code = serializers.CharField(max_length=6)
    # 인증번호의 유효성을 검사
    def validate(self, data):
        try:
            # 해당 이메일과 인증번호로 인증 레코드를 조회
            verification = EmailVerification.objects.get(
                email=data['email'], 
                verification_code=data['verification_code']
            )
            # 인증번호 만료 확인
            if verification.is_expired():
                raise serializers.ValidationError("인증번호가 만료되었습니다.")
            
            verification.is_verified = True
            verification.save()
            return data
        
        except EmailVerification.DoesNotExist:
            raise serializers.ValidationError("잘못된 인증번호입니다.")

# 회원가입
class UserSerializer(serializers.ModelSerializer):  # Django REST framework의 ModelSerializer를 상속받아 사용자 정보를 직렬화하는 클래스
    class Meta:  # Meta 클래스는 직렬화할 대상 모델과 필드 정보를 정의
        model = User  # Django의 내장 User 모델을 사용
        fields = '__all__'

    def create(self, validated_data):  # 새 사용자를 생성하는 메서드로, 사용자 비밀번호를 안전하게 저장하도록 처리
        email = validated_data.get('email')
        verification = EmailVerification.objects.filter(
            email=email, 
            is_verified=True
        ).first()
        
        if not verification:
            raise serializers.ValidationError("이메일 인증이 필요합니다.")
        
        user = super().create(validated_data)  # 기본 직렬화 클래스의 `create` 메서드를 호출하여 사용자 객체 생성
        user.set_password(validated_data['password'])  # 비밀번호를 해싱하여 저장. Django의 `set_password` 메서드는 암호화를 처리
        user.is_email_verified = True # 이메일 인증유무 확인
        user.save()  # 변경된 비밀번호를 포함하여 사용자 객체를 데이터베이스에 저장
        return user  # 새로 생성된 사용자 객체를 반환
    
class CustomObtainPairSerializer(TokenObtainPairSerializer):  # JWT 토큰을 생성하는 기본 Serializer를 상속받아 커스터마이징
    @classmethod  # 클래스 메서드로 정의하여 클래스 자체에서 호출되도록 설정
    def get_token(cls, user):  # 사용자로부터 JWT 토큰을 생성하는 메서드
        token = super().get_token(user)  # 부모 클래스의 `get_token` 메서드를 호출하여 기본 토큰 생성
        token['username'] = user.username  # 생성된 토큰에 사용자 이메일을 추가
        token['is_admin'] = user.is_admin  # 사용자 객체의 `is_admin` 속성을 토큰에 포함. (관리자 여부를 판단하는 용도)
        return token  # 수정된 토큰을 반환
    
class CustomObtainPairSerializer(TokenObtainPairSerializer):  # JWT 토큰을 생성하는 기본 Serializer를 상속받아 커스터마이징
    @classmethod  # 클래스 메서드로 정의하여 클래스 자체에서 호출되도록 설정
    def get_token(cls, user):  # 사용자로부터 JWT 토큰을 생성하는 메서드
        token = super().get_token(user)  # 부모 클래스의 `get_token` 메서드를 호출하여 기본 토큰 생성
        token['email'] = user.email  # 생성된 토큰에 사용자 이메일을 추가
        token['is_admin'] = user.is_admin  # 사용자 객체의 `is_admin` 속성을 토큰에 포함. (관리자 여부를 판단하는 용도)
        return token  # 수정된 토큰을 반환
    
# 프로필 
class UserProfileSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
        
# 프로필 수정
class UserProfileUpdateSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'phone', 'birth')