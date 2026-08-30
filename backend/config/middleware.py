"""Dependency-free CORS for the hackathon frontend.

This is a fun/side project, so the API intentionally answers every cross-origin
request with ``Access-Control-Allow-Origin: *`` (fine for a demo; do not reuse
in a production service).
"""

from django.http import HttpResponse

_ALLOW_METHODS = "GET, POST, OPTIONS"
_ALLOW_HEADERS = "Content-Type, Accept, Origin"


class DemoCORSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse(status=200)
        else:
            response = self.get_response(request)

        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = _ALLOW_METHODS
        response["Access-Control-Allow-Headers"] = _ALLOW_HEADERS
        response["Access-Control-Max-Age"] = "86400"
        return response