from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, JsonResponse


def manifest_view(request):
    """Serve manifest.json from the site root so PWA install works."""
    import json, os
    path = settings.BASE_DIR / "static" / "manifest.json"
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        return JsonResponse(data, content_type="application/manifest+json")
    return HttpResponse("{}", content_type="application/manifest+json", status=404)


def sw_view(request):
    """Serve service worker from the site root (required scope)."""
    sw_path = settings.BASE_DIR / "static" / "sw.js"
    if sw_path.exists():
        content = sw_path.read_text(encoding="utf-8")
    else:
        content = "// service worker placeholder"
    return HttpResponse(content, content_type="application/javascript")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("donations.urls")),
    path("manifest.json", manifest_view, name="manifest"),
    path("sw.js", sw_view, name="sw"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
