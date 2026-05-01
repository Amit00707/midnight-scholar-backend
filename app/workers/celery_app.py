"""
Celery Application — Stub for production without Redis/Celery
=============================================================
Celery is disabled on Render free tier.
Background tasks fall back to direct execution.
"""


class _CeleryStub:
    """No-op stub when Celery is not available."""
    def task(self, *args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

    def send_task(self, *args, **kwargs):
        pass


celery_app = _CeleryStub()
