import hashlib
import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel


def content_hash(content: str | bytes) -> str:
    encoded_content = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(encoded_content).hexdigest()


def specification_hash(specification: BaseModel | Mapping[str, Any]) -> str:
    if isinstance(specification, BaseModel):
        value = specification.model_dump(mode="json", by_alias=True)
    else:
        value = dict(specification)

    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return content_hash(serialized)
