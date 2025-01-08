from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from user.models import User

# 회원가입
class UserSerializer(serializers.ModelSerializer):  # Django REST framework의 ModelSerializer를 상속받아 사용자 정보를 직렬화하는 클래스
    class Meta:  # Meta 클래스는 직렬화할 대상 모델과 필드 정보를 정의
        model = User  # Django의 내장 User 모델을 사용
        fields = '__all__'  # User 모델의 모든 필드를 직렬화 대상으로 설정

    def create(self, validated_data):  # 새 사용자를 생성하는 메서드로, 사용자 비밀번호를 안전하게 저장하도록 처리
        user = super().create(validated_data)  # 기본 직렬화 클래스의 `create` 메서드를 호출하여 사용자 객체 생성
        password = user.password  # 사용자 입력으로 받은 비밀번호를 가져옴
        user.set_password(password)  # 비밀번호를 해싱하여 저장. Django의 `set_password` 메서드는 암호화를 처리
        user.save()  # 변경된 비밀번호를 포함하여 사용자 객체를 데이터베이스에 저장
        return user  # 새로 생성된 사용자 객체를 반환
    
class CustomObtainPairSerializer(TokenObtainPairSerializer):  # JWT 토큰을 생성하는 기본 Serializer를 상속받아 커스터마이징
    @classmethod  # 클래스 메서드로 정의하여 클래스 자체에서 호출되도록 설정
    def get_token(cls, user):  # 사용자로부터 JWT 토큰을 생성하는 메서드
        token = super().get_token(user)  # 부모 클래스의 `get_token` 메서드를 호출하여 기본 토큰 생성
        token['email'] = user.email  # 생성된 토큰에 사용자 이메일을 추가
        token['is_admin'] = user.is_admin  # 사용자 객체의 `is_admin` 속성을 토큰에 포함. (관리자 여부를 판단하는 용도)
        return token  # 수정된 토큰을 반환