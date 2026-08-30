"""API routes.

Both trailing-slash and non-trailing-slash forms are registered so clients are
not forced into a redirect.
"""

from django.urls import path

from . import views


def _slashable(view, base: str):
    return [path(base + "/", view), path(base, view)]


urlpatterns = [
    *_slashable(views.AnalysisListCreateView.as_view(), "analyses"),
    *_slashable(views.AnalysisDetailView.as_view(), "analyses/<int:pk>"),
    *_slashable(
        views.FindingReviewView.as_view(),
        "analyses/<int:pk>/findings/<int:finding_id>/review",
    ),
    *_slashable(
        views.ReviewSummaryView.as_view(),
        "analyses/<int:pk>/review-summary",
    ),
    *_slashable(views.HealthView.as_view(), "health"),
]