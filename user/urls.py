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
    path('search-users/', views.SearchUserView.as_view(), name='search_users'),  # 사용자 검색 API
    path('send_friend_request/', views.SendFriendRequestView.as_view(), name='send_friend_request'), # 친구 요청 API
    path('sent-friend-requests/', views.SentFriendRequestListView.as_view(), name='sent_friend_request_list'),  # 보낸 친구 요청 목록 API
    path('received-friend-requests/', views.ReceivedFriendRequestListView.as_view(), name='received_friend_request_list'),  # 받은 친구 요청 목록 API
    path('accept_friend_request/', views.AcceptFriendRequestView.as_view(), name='accept_friend_request'), # 친구 요청 수락 API
    path('reject-friend-request/', views.RejectFriendRequestView.as_view(), name='reject_friend_request'),  # 친구 요청 거절 API
    path('friends/', views.FriendListView.as_view(), name='friend_list'),  # 친구 목록 API
    path('delete-friend/', views.DeleteFriendView.as_view(), name='delete-friend'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
]