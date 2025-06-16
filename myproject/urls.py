from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('shift_pilot/admin/', admin.site.urls),
    path('',include('portfolio.urls')),
    path('shift_pilot/accounts/', include('accounts.urls')),
]
