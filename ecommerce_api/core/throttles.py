import shortuuid
from rest_framework.throttling import SimpleRateThrottle


class ComboRateThrottle(SimpleRateThrottle):
    scope = "combo"

    def get_cache_key(self, request, view):
        # 1. IP address
        ip = self.get_ident(request)

        # 2. User (from Djoser auth)
        if request.user and request.user.is_authenticated:
            user_id = str(request.user.id)
        else:
            user_id = "anonymous"

        # 3. Device ID (shortuuid-based)
        device_id = request.headers.get("X-Device-ID")

        if not device_id:
            # fallback if frontend doesn't send it
            device_id = f"device_{shortuuid.uuid()}"

        # 4. API key (web, mobile, admin, etc.)
        api_key = request.headers.get("X-API-KEY", "public")

        # Combine everything
        combo_identity = f"{ip}:{user_id}:{device_id}:{api_key}"

        return self.cache_format % {
            "scope": self.scope,
            "ident": combo_identity,
        }
