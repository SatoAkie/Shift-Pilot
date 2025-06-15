from django.db import models
from django.contrib.auth.models import(
    AbstractBaseUser, PermissionsMixin,BaseUserManager
)

class UserManager(BaseUserManager):
        def create_user(self, email, password=None, **extra_fields):
            if not email:
                raise ValueError('メールアドレスは必須です')
            user = self.model(email=email,**extra_fields)
            user .set_password(password)
            user.save()
            return user
        
        def create_superuser(self, email, password=None, **extra_fields):
            extra_fields.setdefault('is_staff', True)
            extra_fields.setdefault('is_active', True)
            return self.create_user(email, password=None, **extra_fields)
        
class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=128)
    email =  models.EmailField(max_length=128, unique=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta: 
        db_table = 'user'
    