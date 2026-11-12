"""
Permissions for MockMate REST APIs.
"""

from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Object-level permission allowing only the owner of an object to access or modify it.
    Assumes the model instance has a `user` foreign key.
    """

    def has_object_permission(self, request, view, obj):
        return getattr(obj, "user", None) == request.user

