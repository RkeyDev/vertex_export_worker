import os
import redis
import json
import logging
from typing import Union, Any, Optional
from app.dataTypes.OperationResult import OperationResult

logger = logging.getLogger(__name__)


class RedisManager:

    EXPORT_QUEUE_KEY = "export:queue"
    DEFAULT_HOST = os.environ.get("REDIS_HOST", "localhost")
    DEFAULT_PORT = int(os.environ.get("REDIS_PORT", 6379))
    DEFAULT_DB = 0

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, db: int = DEFAULT_DB, password: Optional[str] = None):
        self._client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password or None,
            decode_responses=True,
        )

    def getFirstFromQueue(self, queue_key: str = EXPORT_QUEUE_KEY) -> Union[str, None]:
        try:
            return self._client.lpop(queue_key)
        except redis.RedisError as e:
            logger.error("getFirstFromQueue failed: %s", e)
            return None

    def blockingGetFirstFromQueue(self, queue_key: str = EXPORT_QUEUE_KEY, timeout: int = 0) -> Union[str, None]:
        try:
            result = self._client.blpop(queue_key, timeout=timeout)
            return result[1] if result else None
        except redis.RedisError as e:
            logger.error("blockingGetFirstFromQueue failed: %s", e)
            return None

    def pushToQueue(self, queue_key: str = EXPORT_QUEUE_KEY, *values: str) -> OperationResult:
        try:
            self._client.rpush(queue_key, *values)
            return OperationResult.SUCCEED
        except redis.RedisError as e:
            logger.error("pushToQueue failed: %s", e)
            return OperationResult.FAILED

    def getQueueLength(self, queue_key: str = EXPORT_QUEUE_KEY) -> int:
        try:
            return self._client.llen(queue_key)
        except redis.RedisError as e:
            logger.error("getQueueLength failed: %s", e)
            return -1

    def addKeyValue(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> OperationResult:
        try:
            serialised = json.dumps(value)
            if ttl_seconds:
                self._client.setex(key, ttl_seconds, serialised)
            else:
                self._client.set(key, serialised)
            return OperationResult.SUCCEED
        except (redis.RedisError, TypeError) as e:
            logger.error("addKeyValue failed for key '%s': %s", key, e)
            return OperationResult.FAILED

    def getValue(self, key: str) -> Union[Any, None]:
        try:
            raw = self._client.get(key)
            return json.loads(raw) if raw is not None else None
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error("getValue failed for key '%s': %s", key, e)
            return None

    def deleteKey(self, key: str) -> OperationResult:
        try:
            self._client.delete(key)
            return OperationResult.SUCCEED
        except redis.RedisError as e:
            logger.error("deleteKey failed for key '%s': %s", key, e)
            return OperationResult.FAILED

    def keyExists(self, key: str) -> bool:
        try:
            return bool(self._client.exists(key))
        except redis.RedisError as e:
            logger.error("keyExists failed for key '%s': %s", key, e)
            return False

    def setTTL(self, key: str, ttl_seconds: int) -> OperationResult:
        try:
            if not self._client.expire(key, ttl_seconds):
                return OperationResult.FAILED
            return OperationResult.SUCCEED
        except redis.RedisError as e:
            logger.error("setTTL failed for key '%s': %s", key, e)
            return OperationResult.FAILED

    def hashSet(self, hash_key: str, field: str, value: Any) -> OperationResult:
        try:
            self._client.hset(hash_key, field, json.dumps(value))
            return OperationResult.SUCCEED
        except (redis.RedisError, TypeError) as e:
            logger.error("hashSet failed: %s", e)
            return OperationResult.FAILED

    def hashGet(self, hash_key: str, field: str) -> Union[Any, None]:
        try:
            raw = self._client.hget(hash_key, field)
            return json.loads(raw) if raw is not None else None
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error("hashGet failed: %s", e)
            return None

    def hashGetAll(self, hash_key: str) -> dict:
        try:
            raw = self._client.hgetall(hash_key)
            return {k: json.loads(v) for k, v in raw.items()}
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error("hashGetAll failed: %s", e)
            return {}

    def publish(self, channel: str, message: Any) -> OperationResult:
        try:
            self._client.publish(channel, json.dumps(message))
            return OperationResult.SUCCEED
        except (redis.RedisError, TypeError) as e:
            logger.error("publish failed on channel '%s': %s", channel, e)
            return OperationResult.FAILED

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except redis.RedisError:
            return False