from django.db import models
from django.contrib.auth.models import(
    AbstractBaseUser, PermissionsMixin,BaseUserManager
)
from django.conf import settings
import uuid

class UserManager(BaseUserManager):
        def create_user(self, email, password, **extra_fields):
            if not email:
                raise ValueError('メールアドレスは必須です')
            user = self.model(email=email,**extra_fields)
            user .set_password(password)
            user.save()
            return user
        
        def create_superuser(self, email, password, **extra_fields):
            extra_fields.setdefault('is_staff', True)
            extra_fields.setdefault('is_active', True)
            return self.create_user(email, password, **extra_fields)
        
class Role(models.Model):
    role_name = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.role_name

class Team(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Team{self.id}"
        
class User(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=128)
    email =  models.EmailField(max_length=128, unique=True)
    password = models.CharField(max_length=128)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    profile_image = models.ImageField(upload_to='profile_images', null=True, blank=True)

    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta: 
        db_table = 'user'

class Invitation(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    team = models.ForeignKey('Team', on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)    
    updated_at = models.DateTimeField(auto_now=True)

    is_used = models.BooleanField(default=False)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_invitations'
    )