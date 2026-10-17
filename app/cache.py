"""Redis access."""
import json
import logging
import os

import redis

log = logging.getLogger(__name__)

_client = None


def client():
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
    return _client


def get_json(key):
    """Cached value, or None on a miss. A Redis outage counts as a miss."""
    try:
        raw = client().get(key)
    except redis.RedisError as e:
        log.warning("cache read failed: %s", e)
        return None
    return json.loads(raw) if raw else None


def set_json(key, value, ttl=300):
    try:
        client().set(key, json.dumps(value, default=str), ex=ttl)
    except redis.RedisError as e:
        log.warning("cache write failed: %s", e)


def drop(*keys):
    if keys:
        try:
            client().delete(*keys)
        except redis.RedisError as e:
            log.warning("cache drop failed: %s", e)


def drop_prefix(prefix):
    """Delete every key under a prefix. Stale entries expire via their TTL
    if Redis is unreachable at this moment."""
    try:
        c = client()
        keys = list(c.scan_iter(f"{prefix}*"))
        if keys:
            c.delete(*keys)
    except redis.RedisError as e:
        log.warning("cache invalidation failed: %s", e)
