"""Image generation provider abstraction.

ImageProvider protocol + two implementations:
  - MockImageProvider  — deterministic, zero-latency, used by default
  - FalAIProvider      — calls fal.ai REST API; requires FAL_API_KEY

Usage in service layer: always call through ImageGenerationService,
which enforces exactly-4-variants and handles per-variant error recovery.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------


@dataclass
class GenerationParams:
    """Per-variant inputs to the image provider."""

    prompt: str
    negative_prompt: str
    width: int
    height: int
    seed: int | None = None  # None = provider picks a random seed


@dataclass
class GenerationResult:
    """What comes back from a single generation call."""

    success: bool
    image_url: str | None           # relative /cache/… URL served by StaticFiles
    image_path: str | None          # absolute local filesystem path
    provider_request_id: str | None  # fal request_id or mock UUID
    generation_seed: int | None
    generation_time_ms: int
    model_used: str
    provider_name: str
    error: str | None = None


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class ImageProvider(Protocol):
    """Single-method interface all image backends must implement."""

    provider_name: str

    async def generate(
        self,
        params: GenerationParams,
        *,
        output_dir: Path,
        variant_number: int,
        session_id: uuid.UUID,
    ) -> GenerationResult: ...


# ---------------------------------------------------------------------------
# MockImageProvider
# ---------------------------------------------------------------------------

_MOCK_PLACEHOLDER = (
    "data:image/svg+xml;charset=utf-8,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='480'%3E"
    "%3Crect width='400' height='480' fill='%230A1A3F'/%3E"
    "%3Ctext x='200' y='240' font-size='24' fill='%23E8C547' "
    "text-anchor='middle' dominant-baseline='middle'%3EMock Variant%3C/text%3E"
    "%3C/svg%3E"
)


class MockImageProvider:
    """Deterministic provider for development and testing.

    Does not call any external API. Records all calls for test introspection.
    """

    provider_name = "mock"

    def __init__(self, latency_ms: int = 0) -> None:
        self._latency_ms = latency_ms
        self.calls: list[dict[str, Any]] = []

    async def generate(
        self,
        params: GenerationParams,
        *,
        output_dir: Path,
        variant_number: int,
        session_id: uuid.UUID,
    ) -> GenerationResult:
        if self._latency_ms:
            await asyncio.sleep(self._latency_ms / 1000)

        seed = params.seed if params.seed is not None else (variant_number * 1337 + 42)
        request_id = str(uuid.uuid4())
        self.calls.append(
            {
                "params": params,
                "variant_number": variant_number,
                "session_id": session_id,
                "request_id": request_id,
                "seed": seed,
            }
        )

        return GenerationResult(
            success=True,
            image_url=f"/cache/designs/{session_id}/variant_{variant_number}_mock.svg",
            image_path=str(output_dir / f"variant_{variant_number}_mock.svg"),
            provider_request_id=request_id,
            generation_seed=seed,
            generation_time_ms=self._latency_ms,
            model_used="mock",
            provider_name=self.provider_name,
        )


# ---------------------------------------------------------------------------
# FalAIProvider
# ---------------------------------------------------------------------------


class FalAIProvider:
    """fal.ai hosted inference provider.

    Uses the queue-based REST API:
      POST /fal-ai/flux/dev  → {request_id}
      GET  /requests/{request_id}/status  → poll until COMPLETED
      GET  /requests/{request_id}         → {images: [{url}], seed: int}

    Disabled unless FAL_API_KEY is set (checked at startup).
    """

    provider_name = "fal_ai"
    _BASE_URL = "https://queue.fal.run"
    _MODEL = "fal-ai/flux/dev"
    _POLL_INTERVAL_S = 2.0
    _TIMEOUT_S = 120.0

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._headers = {
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        }

    async def generate(
        self,
        params: GenerationParams,
        *,
        output_dir: Path,
        variant_number: int,
        session_id: uuid.UUID,
    ) -> GenerationResult:
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=30) as client:
            # Submit generation request
            submit_resp = await client.post(
                f"{self._BASE_URL}/{self._MODEL}",
                headers=self._headers,
                json={
                    "prompt": params.prompt,
                    "negative_prompt": params.negative_prompt,
                    "width": params.width,
                    "height": params.height,
                    **({"seed": params.seed} if params.seed is not None else {}),
                    "num_images": 1,
                    "enable_safety_checker": False,
                },
            )
            if submit_resp.status_code not in (200, 202):
                return GenerationResult(
                    success=False,
                    image_url=None,
                    image_path=None,
                    provider_request_id=None,
                    generation_seed=None,
                    generation_time_ms=int((time.monotonic() - t0) * 1000),
                    model_used=self._MODEL,
                    provider_name=self.provider_name,
                    error=f"fal.ai submit failed: HTTP {submit_resp.status_code}",
                )
            request_id: str = submit_resp.json()["request_id"]

        # Poll for completion
        deadline = time.monotonic() + self._TIMEOUT_S
        result_data: dict[str, Any] | None = None
        async with httpx.AsyncClient(timeout=10) as client:
            while time.monotonic() < deadline:
                await asyncio.sleep(self._POLL_INTERVAL_S)
                status_resp = await client.get(
                    f"{self._BASE_URL}/requests/{request_id}/status",
                    headers=self._headers,
                )
                if status_resp.status_code != 200:
                    continue
                status = status_resp.json().get("status")
                if status == "COMPLETED":
                    result_resp = await client.get(
                        f"{self._BASE_URL}/requests/{request_id}",
                        headers=self._headers,
                    )
                    if result_resp.status_code == 200:
                        result_data = result_resp.json()
                    break
                if status == "FAILED":
                    break

        elapsed_ms = int((time.monotonic() - t0) * 1000)

        if result_data is None:
            return GenerationResult(
                success=False,
                image_url=None,
                image_path=None,
                provider_request_id=request_id,
                generation_seed=None,
                generation_time_ms=elapsed_ms,
                model_used=self._MODEL,
                provider_name=self.provider_name,
                error="fal.ai generation timed out or failed",
            )

        # Download image to local cache
        fal_image_url: str = result_data["images"][0]["url"]
        generation_seed: int | None = result_data.get("seed")
        filename = f"variant_{variant_number}_{request_id[:8]}.png"
        local_path = output_dir / filename
        relative_url = f"/cache/designs/{session_id}/{filename}"

        try:
            async with httpx.AsyncClient(timeout=60) as dl_client:
                img_resp = await dl_client.get(fal_image_url)
                img_resp.raise_for_status()
                output_dir.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(img_resp.content)
        except Exception as exc:
            return GenerationResult(
                success=False,
                image_url=None,
                image_path=None,
                provider_request_id=request_id,
                generation_seed=generation_seed,
                generation_time_ms=elapsed_ms,
                model_used=self._MODEL,
                provider_name=self.provider_name,
                error=f"Image download failed: {exc}",
            )

        return GenerationResult(
            success=True,
            image_url=relative_url,
            image_path=str(local_path),
            provider_request_id=request_id,
            generation_seed=generation_seed,
            generation_time_ms=elapsed_ms,
            model_used=self._MODEL,
            provider_name=self.provider_name,
        )


# ---------------------------------------------------------------------------
# ImageGenerationService
# ---------------------------------------------------------------------------


@dataclass
class VariantGenerationResult:
    """Per-variant outcome returned to the API layer."""

    variant_number: int
    style: str
    result: GenerationResult


class ImageGenerationService:
    """Orchestrates generation of exactly 4 variants from a DesignStrategy.

    Runs all 4 variants concurrently. Each variant failure is captured
    individually — a single bad variant does not abort the other three.
    """

    def __init__(self, provider: ImageProvider, cache_root: Path) -> None:
        self._provider = provider
        self._cache_root = cache_root

    async def generate_variants(
        self,
        *,
        session_id: uuid.UUID,
        variants: list[Any],  # list[VariantPrompt] — avoid circular import
        seeds: list[int | None] | None = None,
    ) -> list[VariantGenerationResult]:
        """Generate all 4 variants concurrently.

        Args:
            session_id: Used for output directory path and logging.
            variants:   Exactly 4 VariantPrompt objects from DesignStrategy.
            seeds:      Optional per-variant seeds (for deterministic replay).
                        If shorter than variants, remaining are None (random).

        Returns:
            List of 4 VariantGenerationResult in input order.
        """
        if len(variants) != 4:
            raise ValueError(f"Expected exactly 4 variants, got {len(variants)}")

        seeds_list: list[int | None] = list(seeds) if seeds else []
        while len(seeds_list) < 4:
            seeds_list.append(None)

        output_dir = self._cache_root / str(session_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        async def _generate_one(
            idx: int, variant: Any
        ) -> VariantGenerationResult:
            params = GenerationParams(
                prompt=variant.prompt,
                negative_prompt=variant.negative_prompt,
                width=variant.width,
                height=variant.height,
                seed=seeds_list[idx],
            )
            try:
                result = await self._provider.generate(
                    params,
                    output_dir=output_dir,
                    variant_number=idx + 1,
                    session_id=session_id,
                )
            except Exception as exc:
                result = GenerationResult(
                    success=False,
                    image_url=None,
                    image_path=None,
                    provider_request_id=None,
                    generation_seed=None,
                    generation_time_ms=0,
                    model_used="unknown",
                    provider_name=self._provider.provider_name,
                    error=str(exc),
                )
            return VariantGenerationResult(
                variant_number=idx + 1,
                style=variant.style.value,
                result=result,
            )

        return list(await asyncio.gather(*[_generate_one(i, v) for i, v in enumerate(variants)]))
