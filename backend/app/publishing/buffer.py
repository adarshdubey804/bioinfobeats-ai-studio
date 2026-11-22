"""Minimal Buffer GraphQL adapter. Secrets remain server-side."""
from typing import Any
import httpx
from app.core.config import settings

class BufferConfigurationError(RuntimeError):
    pass

class BufferAPIError(RuntimeError):
    pass

def graphql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    if not settings.buffer_access_token:
        raise BufferConfigurationError("BUFFER_ACCESS_TOKEN is not configured.")
    response = httpx.post(
        settings.buffer_api_base_url,
        headers={"Authorization": f"Bearer {settings.buffer_access_token}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise BufferAPIError(str(payload["errors"])[:1500])
    return payload.get("data", {})

def list_channels() -> dict[str, Any]:
    query = """
    query BioinfoBeatsChannels {
      account {
        organizations {
          id
          channels {
            id
            name
            service
          }
        }
      }
    }
    """
    return graphql(query)

def create_post(channel_id: str, text: str, due_at: str | None = None, publish_now: bool = False) -> dict[str, Any]:
    mode = "shareNow" if publish_now else "customScheduled"
    query = """
    mutation BioinfoBeatsCreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post { id text status dueAt externalLink }
        }
        ... on MutationError { message }
      }
    }
    """
    input_data: dict[str, Any] = {
        "channelId": channel_id,
        "text": text,
        "schedulingType": "automatic",
        "mode": mode,
        "aiAssisted": True,
    }
    if not publish_now:
        input_data["dueAt"] = due_at
    result = graphql(query, {"input": input_data}).get("createPost")
    if not result:
        raise BufferAPIError("Buffer returned an empty createPost response.")
    if result.get("message"):
        raise BufferAPIError(result["message"])
    if not result.get("post"):
        raise BufferAPIError(f"Unexpected Buffer createPost response: {result}")
    return result["post"]
