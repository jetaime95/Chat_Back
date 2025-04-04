from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from user.models import User, EmailVerification, Friendship
from user.utils import send_verification_email
import re
import random

# 이메일 요청
class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def create(self, validated_data):
        email = validated_data['email']
        EmailVerification.objects.filter(email=email).delete()
        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        email_verification = EmailVerification.objects.create(
            email=email,
            verification_code=verification_code
        )
        send_verification_email(email, verification_code)
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
    password = serializers.CharField(write_only=True)
    
    class Meta:  # Meta 클래스는 직렬화할 대상 모델과 필드 정보를 정의
        model = User  # Django의 내장 User 모델을 사용
        fields = '__all__'

    def validate_password(self, value):
        try:
            return PasswordValidator.validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

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
    
class CustomObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['is_admin'] = user.is_admin

        user.is_online = True
        user.save()

        return token

class PasswordValidator:
    @staticmethod
    def validate_password(password):
        if len(password) < 8:
            raise ValidationError("비밀번호는 최소 8자 이상이어야 합니다.")
        
        if not re.search(r'[A-Za-z]', password):
            raise ValidationError("비밀번호는 영문을 포함해야 합니다.")
            
        if not re.search(r'\d', password):
            raise ValidationError("비밀번호는 숫자를 포함해야 합니다.")
            
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("비밀번호는 특수문자를 포함해야 합니다.")
            
        return password
    
# 새 비밀번호 재설정 시리얼라이저
class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate_new_password(self, value):
        return PasswordValidator.validate_password(value)
    
    def validate(self, data):
        # 새 비밀번호와 확인 비밀번호 일치 확인
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("새 비밀번호가 일치하지 않습니다.")
        
        # 이메일 인증 확인
        if not EmailVerification.objects.filter(email=data['email'], is_verified=True).exists():
            raise serializers.ValidationError("이메일 인증을 먼저 완료해주세요.")
        
        return data

# 비밀번호 변경
class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    
    def validate_new_password(self, value):
        try:
            return PasswordValidator.validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

    def validate(self, data):
        # 현재 비밀번호와 새 비밀번호가 같은지 확인
        if data['current_password'] == data['new_password']:
            raise serializers.ValidationError("새 비밀번호는 현재 비밀번호와 달라야 합니다.")
        
        return data

# 사용자 검색 및 친구 목록
class UserSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'updated_at', 'is_online', 'image']  # 필요한 필드만 포함

# 친구 요청
class FriendshipSerializer(serializers.ModelSerializer):
    from_user = serializers.StringRelatedField()  # 요청을 보낸 사용자
    to_user = serializers.StringRelatedField()  # 요청을 받은 사용자

    class Meta:
        model = Friendship
        fields = ['from_user', 'to_user', 'created_at', 'accepted']  # 필요한 필드 설정

# 친구 요청 수락, 거절 및 친구 삭제
class FriendRequestActionSerializer(serializers.Serializer):
    username = serializers.CharField()  # 수락 또는 거절할 친구 요청의 사용자 이름

# 프로필 
class UserProfileSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
        
# 프로필 수정
class UserProfileUpdateSerializers(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)

    class Meta:
        model = User
        fields = ('username', 'phone', 'birth', 'image')