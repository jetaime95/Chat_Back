from django.db import models
from django.contrib.auth.models import(BaseUserManager, AbstractBaseUser)
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta

# Django의 기본 User Manager를 확장하여 사용자 생성 로직을 커스터마이징하는 클래스.
class UserManager(BaseUserManager):
    # 일반user 생성 메서드
    def create_user(self, username, email, password=None):
        # username이 제공되지 않을 경우 예외처리
        if not username:
            raise ValueError('username이 필요합니다.')
        
        # email이 제공되지 않을 경우 예외처리
        if not email:
            raise ValueError('email이 필요합니다.')
        
        # user 인스턴스를 생성하고 email을 표준 형식으로 처리
        user = self.model(
            username = username,
            email = self.normalize_email(email),
        )
        # user의 password 해쉬처리
        user.set_password(password)
        # DB에 user 정보를 저장
        user.save(using=self._db)
        return user
    
    # superuser 생성 메서드
    def create_superuser(self, username, email, password=None):
        # create_user 메서드 실행하여 생성
        user = self.create_user(
            email,
            password=password,
        )
        # 생성된 user model의 is_admin이 True면 superuser 처리 
        user.is_admin = True
        user.save(using=self._db)
        return user
    
class EmailVerification(models.Model):
    email = models.EmailField(unique=True)
    verification_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    def is_expired(self):
        # 인증번호 유효시간 설정
        return self.created_at < timezone.now() - timedelta(minutes=10)
    
class User(AbstractBaseUser):
    GENDERS = (
        ('남성', 'male'),('여성', 'female'),
    )
    phoneNumberRegex = RegexValidator(regex = r'^01([0|1|6|7|8|9]?)-?([0-9]{3,4})-?([0-9]{4})$')
    email = models.EmailField(max_length=255,unique=True, verbose_name='이메일')
    username = models.CharField(max_length=50, unique=True, verbose_name='이름')
    gender = models.CharField(verbose_name='성별', max_length=6, choices=GENDERS)
    phone = models.CharField(validators = [phoneNumberRegex], max_length = 11)
    birth = models.DateField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_admin = models.BooleanField(default=False)

    # 사용자 생성과 관련된 로직을 처리하는 UserManager를 설정
    objects = UserManager()

    USERNAME_FIELD = 'email' # username_field를 email로 변경
    REQUIRED_FIELDS = ['username']

    # 사용자 객체를 문자열로 표현할 때 호출되는 메서드
    def __str__(self):
        return self.username
    
    # 사용자가 특정 권한을 가지고 있는지 확인
    def has_perm(self, perm, obj=None):
        return True
    
    # 사용자가 특정 애플리케이션에 대한 권한을 가지고 있는지 확인
    def has_module_perms(self, app_label):
        return True
    
    @property
    def is_staff(self):
        return self

class Friendship(models.Model):
    from_user = models.ForeignKey(User, related_name='friends_from', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='friends_to', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)  # 친구 요청 수락 여부

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['from_user', 'to_user'], name='unique_friendship')
        ]

    def __str__(self):
            return f"{self.from_user.username} -> {self.to_user.username} ({'Accepted' if self.accepted else 'Pending'})"