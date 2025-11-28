from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Ecommerce API",
        default_version="v1",
        description="API documentation for Ecommerce management system",
        contact=openapi.Contact(email="Kellytwinzzy@gmail.com"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("admin/", admin.site.urls),
    #  Djoser authentication routes (global)
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),

    #  Your custom user/profile API routes
    path("api/", include("users.urls")),
    path("api/", include("product.urls")),
    path("api/", include("carts.urls")),
    path("api/", include("orders.urls")),
    path("api/", include("services.urls")),
    
    # Swagger docs
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
