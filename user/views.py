from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from user.models import User
from user.serializers import UserSerializer, CustomObtainPairSerializer

#회원가입
class UserView(APIView):
    def post(self, request):
        if User.objects.filter(email = request.data["email"]):
            return Response({"message" : "이미 가입된 이메일 입니다.\n다시 시도해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        
        elif User.objects.filter(username = request.data["username"]):
            return Response({"message" : "중복된 닉네임이 있습니다.\n다시 시도해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        
        else:
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({"message" : "회원가입을 축하합니다!"}, status=status.HTTP_201_CREATED)
            else:
                return Response({"message" : f"${serializer.errors}"}, status=status.HTTP_400_BAD_REQUEST)

# 로그인인       
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomObtainPairSerializer