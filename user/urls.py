from django.urls import path
from user import views
from rest_framework_simplejwt.views import TokenRefreshView

app_name = "user"
urlpatterns = [
    path('token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('email-verification/', views.EmailVerificationView.as_view(), name='email-verification'),
    path('verify-code/', views.VerifyCodeView.as_view(), name='verify-code'),
    path('signup/', views.UserView.as_view(), name='user_view'),
    path('profile/', views.ProfileView.as_view(), name='profile_view'),
]