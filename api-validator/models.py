from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ParameterMeta:
    name: str
    location: str
    required: bool = False
    schema: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["in"] = payload.pop("location")
        return payload


@dataclass
class RequestBodyMeta:
    required: bool = False
    content_type: str = "application/json"
    schema: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResponseMeta:
    status_code: str
    content_type: str = "application/json"
    schema: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApiMeta:
    endpoint: str
    method: str
    operation_id: str
    summary: str = ""
    tags: List[str] = field(default_factory=list)
    headers: List[ParameterMeta] = field(default_factory=list)
    query_params: List[ParameterMeta] = field(default_factory=list)
    path_params: List[ParameterMeta] = field(default_factory=list)
    request_body: Optional[RequestBodyMeta] = None
    responses: List[ResponseMeta] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["headers"] = [h.to_dict() for h in self.headers]
        payload["query_params"] = [q.to_dict() for q in self.query_params]
        payload["path_params"] = [p.to_dict() for p in self.path_params]
        payload["request_body"] = self.request_body.to_dict() if self.request_body else None
        payload["responses"] = [r.to_dict() for r in self.responses]
        return payload
