from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import Activity_log
from common.utils import get_client_ip
from pyddns.models import SubDomain

from .serializers import (
    ActivityLogSerializer,
    IPUpdateSerializer,
    SubDomainSerializer,
    UserSerializer,
)


User = get_user_model()


class CurrentUserView(APIView):
    """GET /api/me/ — current user profile."""

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class TokenRevokeView(APIView):
    """POST /api/auth/token/revoke/ — invalidate the current token."""

    def post(self, request):
        token = getattr(request.user, 'auth_token', None)
        if token is not None:
            token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IsOwnerOrAdmin(permissions.BasePermission):
    """Allow access only to the object's owner, or any superuser."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return getattr(obj, 'user', None) == request.user


class SubDomainViewSet(viewsets.ModelViewSet):
    """CRUD over the caller's own subdomains.

    Admins see and manage all subdomains. Anyone authenticated can update
    the IP of one of their own subdomains via the `update_ip` action.
    """

    serializer_class = SubDomainSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        qs = SubDomain.objects.all().order_by('name')
        if not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def update_ip(self, request, pk=None):
        """POST /api/subdomains/<id>/update_ip/ {"ip": "1.2.3.4"}"""
        # Lazy import to avoid circular dependency at module load time.
        from pyddns.views import set_ip

        subdomain = self.get_object()
        serializer = IPUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip = serializer.validated_data['ip']

        domain = f"{subdomain.name}.{settings.DNS_DOMAIN}"
        return_code, message = set_ip(request, domain, ip)

        Activity_log.objects.create(
            action='SYNC',
            ip=ip,
            code=return_code,
            xforward=get_client_ip(request),
            user_affected=request.user.username,
            domain=domain,
            agent=request.META.get('HTTP_USER_AGENT', ''),
            result=message,
        )

        return Response({'code': return_code, 'message': message})


class UserViewSet(viewsets.ModelViewSet):
    """Admin-only user management."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all().order_by('username')


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only audit log. Non-admins see only their own entries."""

    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Activity_log.objects.all().order_by('-id_log')
        if not self.request.user.is_superuser:
            qs = qs.filter(user_affected=self.request.user.username)
        return qs
