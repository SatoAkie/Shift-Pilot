from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('shift_pilot/admin/', admin.site.urls),
    path('',include('portfolio.urls')),
    path('shift_pilot/accounts/', include('accounts.urls')),
    path('shift_pilot/shifts/', include('shifts.urls')),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
