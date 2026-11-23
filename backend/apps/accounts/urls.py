from django.urls import path

from .views import (
    AdminUserDetailView,
    AdminUserListView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    RefreshView,
    RegisterAssociationView,
    RegisterMerchantView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("register/association/", RegisterAssociationView.as_view(), name="auth-register-association"),
    path("register/merchant/", RegisterMerchantView.as_view(), name="auth-register-merchant"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("password/", PasswordChangeView.as_view(), name="auth-password"),
    path("users/", AdminUserListView.as_view(), name="admin-users"),
    path("users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("users/<int:pk>/review/", AdminUserDetailView.as_view(), name="admin-user-review"),
]
