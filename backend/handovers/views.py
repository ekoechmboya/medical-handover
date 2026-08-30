"""API views for the Medical Handover Quality Agent.

The workflow is explicitly human-in-the-loop: the engine produces *candidate*
findings, and a reviewer must accept, reject, or edit them. The API never
presents findings as executed clinical actions.
"""

import os
import threading

from django.db import close_old_connections
from django.shortcuts import get_object_or_404
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Analysis, Finding, FindingReview
from .serializers import (
    AnalysisCreateSerializer,
    AnalysisDetailSerializer,
    AnalysisListSerializer,
    FindingReviewSerializer,
    ReviewSerializer,
    compute_review_summary,
)
from .services.analysis_service import run_analysis


def _bad_request(detail: str, errors) -> Response:
    return Response({"detail": detail, "errors": errors}, status=http_status.HTTP_400_BAD_REQUEST)


def _load_analysis(pk: int) -> Analysis:
    return get_object_or_404(
        Analysis.objects.prefetch_related("findings__review"),
        pk=pk,
    )


def _run_analysis_in_background(analysis_id: int, backend: str | None) -> None:
    """Engine driver for the async create path.

    Runs in a daemon thread so the web worker keeps serving requests while a
    (potentially minutes-long, live-Gemini) run proceeds. Django's DB
    connections are thread-local, so close stale connections at both ends and
    never share the request thread's connection.
    """
    close_old_connections()
    try:
        analysis = Analysis.objects.get(pk=analysis_id)
        run_analysis(analysis, backend_override=backend)
    except Exception:  # noqa: BLE001 - background thread; never crash the worker
        pass
    finally:
        close_old_connections()


class HealthView(APIView):
    """Lightweight liveness probe (no auth, no DB dependency)."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok", "service": "medical-handover-quality-agent"})


class AnalysisListCreateView(APIView):
    """GET list analyses; POST create and run an analysis."""

    def get(self, request):
        analyses = Analysis.objects.prefetch_related("findings__review")
        data = AnalysisListSerializer(analyses, many=True).data
        return Response({"count": len(data), "results": data})

    def post(self, request):
        serializer = AnalysisCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _bad_request("Invalid analysis input.", serializer.errors)

        data = serializer.validated_data
        analysis = Analysis.objects.create(
            mode=data["mode"],
            status="running",
            patient_profile=data["patient_profile"],
            records=data["records"],
            handover=data["handover"],
        )
        # The engine runs in the background by default: POST returns immediately
        # and the client polls GET /api/analyses/{id}/ until status is terminal.
        # This lets live-Gemini runs exceed any web-request timeout without
        # aborting. Setting MH_ASYNC=0 restores the synchronous path (used by the
        # transaction-isolated test suite and as a deploy escape hatch).
        # Optional per-run emitter choice. When omitted, the server-wide
        # MH_EMITTER_BACKEND env var (default "mock") applies via
        # analysis_service.effective_backend().
        backend = data.get("backend")
        if os.environ.get("MH_ASYNC", "1") == "0":
            run_analysis(analysis, backend_override=backend)
        else:
            threading.Thread(
                target=_run_analysis_in_background,
                args=(analysis.pk, backend),
                daemon=True,
                name=f"analysis-{analysis.pk}",
            ).start()
        analysis = _load_analysis(analysis.pk)
        return Response(
            AnalysisDetailSerializer(analysis).data,
            status=http_status.HTTP_201_CREATED,
        )


class AnalysisDetailView(APIView):
    """GET return one analysis with findings, evidence and review decisions."""

    def get(self, request, pk):
        analysis = _load_analysis(pk)
        return Response(AnalysisDetailSerializer(analysis).data)


class FindingReviewView(APIView):
    """POST review a single finding (accept / reject / edit)."""

    def post(self, request, pk, finding_id):
        analysis = _load_analysis(pk)
        finding = get_object_or_404(Finding, pk=finding_id, analysis=analysis)

        serializer = FindingReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return _bad_request("Invalid review input.", serializer.errors)

        data = serializer.validated_data
        review, _created = FindingReview.objects.update_or_create(
            finding=finding,
            defaults={
                "decision": data["decision"],
                "comment": data.get("comment") or "",
                "edited_summary": data.get("edited_summary") or "",
                "edited_category": data.get("edited_category") or "",
                "edited_status": data.get("edited_status") or "",
                "edited_importance": data.get("edited_importance") or "",
            },
        )
        payload = ReviewSerializer(review).data
        payload["finding_id"] = finding.pk
        payload["analysis_id"] = analysis.pk
        return Response(payload)


class ReviewSummaryView(APIView):
    """GET review counts for an analysis."""

    def get(self, request, pk):
        analysis = _load_analysis(pk)
        return Response(compute_review_summary(analysis))