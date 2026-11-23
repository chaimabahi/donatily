from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class IsAssociation(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "association")


class IsMerchant(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "merchant")


class IsVerifiedUser(BasePermission):
    message = "Le compte doit être vérifié par un administrateur."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_verified or user.role == "admin"))
