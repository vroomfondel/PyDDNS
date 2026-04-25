import re

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers

from common.models import Activity_log
from pyddns.models import SubDomain


User = get_user_model()

SUBDOMAIN_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,62}$')


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_superuser', 'password',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class SubDomainSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    fqdn = serializers.SerializerMethodField()

    class Meta:
        model = SubDomain
        fields = ['id', 'name', 'user', 'fqdn']

    def get_fqdn(self, obj):
        return f"{obj.name}.{settings.DNS_DOMAIN}" if settings.DNS_DOMAIN else obj.name

    def validate_name(self, value):
        if not SUBDOMAIN_RE.match(value):
            raise serializers.ValidationError(
                "must match DNS label pattern: alphanumeric and hyphens, 1-63 chars, no leading hyphen"
            )
        return value


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity_log
        fields = [
            'id_log', 'date', 'action', 'ip', 'xforward',
            'user_affected', 'domain', 'agent', 'code', 'result',
        ]
        read_only_fields = fields


class IPUpdateSerializer(serializers.Serializer):
    ip = serializers.IPAddressField()
