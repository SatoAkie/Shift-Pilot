from django.apps import AppConfig
from django.db.utils import OperationalError,ProgrammingError


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        try:
            from .models import Role
            Role.objects.get_or_create(role_name="管理者")
            Role.objects.get_or_create(role_name="一般")
        except (OperationalError,ProgrammingError):
            pass