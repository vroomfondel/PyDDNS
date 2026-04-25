from django.urls import re_path

from common.views import *

urlpatterns = [
    re_path(r'^logout/', logout, name="logout"),
    re_path(r'^login/', login, name="login"),
    re_path(r'^dologin/', dologin, name="dologin"),
    re_path(r'^permission_denied', permission_denied, name="permission_denied"),
    re_path(r'^sin_permiso', sin_permiso, name="sin_permiso"),
    re_path(r'^$', login),
]
