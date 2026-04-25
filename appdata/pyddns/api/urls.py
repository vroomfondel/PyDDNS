from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r'subdomains', views.SubDomainViewSet, basename='subdomain')
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'activity', views.ActivityLogViewSet, basename='activity')

app_name = 'api'

urlpatterns = [
    path('auth/token/', obtain_auth_token, name='token-obtain'),
    path('auth/token/revoke/', views.TokenRevokeView.as_view(), name='token-revoke'),
    path('me/', views.CurrentUserView.as_view(), name='me'),
    path('', include(router.urls)),
]
