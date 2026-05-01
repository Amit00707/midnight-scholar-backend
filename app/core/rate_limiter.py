"""
Rate Limiter — Redis-backed API Throttling
============================================
Prevents abuse by limiting requests per user/IP via SlowAPI.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
