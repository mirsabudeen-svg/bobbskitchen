"""Unit tests for ImageGenerationService, MockImageProvider, GenerationParams.

No DB, no API, no external calls.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.models.schemas import VariantPrompt, VariantStyle
from app.services.image_gen import (
    GenerationParams,
    GenerationResult,
    ImageGenerationService,
    MockImageProvider,
)


def _make_variant(style: VariantStyle = VariantStyle.ILLUSTRATION, idx: int = 0) -> VariantPrompt:
    return VariantPrompt(
        style=style,
        prompt=f"Test prompt for {style.value} style {idx}",
        negative_prompt="photorealistic, blurry",
        color_palette=["#E8C547", "#0A1A3F"],
        mood="test mood",
        width=4000,
        height=4800,
    )


def _make_four_variants() -> list[VariantPrompt]:
    return [
        _make_variant(VariantStyle.ILLUSTRATION, 0),
        _make_variant(VariantStyle.GEOMETRIC, 1),
        _make_variant(VariantStyle.WATERCOLOR, 2),
        _make_variant(VariantStyle.MINIMALIST, 3),
    ]


# ---------------------------------------------------------------------------
# GenerationParams
# ---------------------------------------------------------------------------


def test_generation_params_defaults():
    params = GenerationParams(prompt="test", negative_prompt="bad", width=100, height=100)
    assert params.seed is None


def test_generation_params_with_seed():
    params = GenerationParams(prompt="test", negative_prompt="bad", width=100, height=100, seed=42)
    assert params.seed == 42


# ---------------------------------------------------------------------------
# MockImageProvider
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_provider_returns_success(tmp_path: Path):
    provider = MockImageProvider()
    params = GenerationParams(prompt="Kerala boat", negative_prompt="blurry", width=400, height=480)
    session_id = uuid.uuid4()
    result = await provider.generate(
        params, output_dir=tmp_path, variant_number=1, session_id=session_id
    )
    assert result.success is True
    assert result.image_url is not None
    assert result.provider_request_id is not None
    assert result.generation_seed is not None
    assert result.provider_name == "mock"


@pytest.mark.asyncio
async def test_mock_provider_records_calls(tmp_path: Path):
    provider = MockImageProvider()
    params = GenerationParams(prompt="test", negative_prompt="bad", width=100, height=100)
    session_id = uuid.uuid4()
    await provider.generate(params, output_dir=tmp_path, variant_number=1, session_id=session_id)
    await provider.generate(params, output_dir=tmp_path, variant_number=2, session_id=session_id)
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_mock_provider_uses_provided_seed(tmp_path: Path):
    provider = MockImageProvider()
    params = GenerationParams(prompt="test", negative_prompt="bad", width=100, height=100, seed=999)
    session_id = uuid.uuid4()
    result = await provider.generate(
        params, output_dir=tmp_path, variant_number=1, session_id=session_id
    )
    assert result.generation_seed == 999


@pytest.mark.asyncio
async def test_mock_provider_url_contains_session_and_variant(tmp_path: Path):
    provider = MockImageProvider()
    params = GenerationParams(prompt="test", negative_prompt="bad", width=100, height=100)
    session_id = uuid.uuid4()
    result = await provider.generate(
        params, output_dir=tmp_path, variant_number=3, session_id=session_id
    )
    assert str(session_id) in result.image_url
    assert "variant_3" in result.image_url


# ---------------------------------------------------------------------------
# ImageGenerationService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_returns_four_variants(tmp_path: Path):
    provider = MockImageProvider()
    svc = ImageGenerationService(provider=provider, cache_root=tmp_path)
    results = await svc.generate_variants(
        session_id=uuid.uuid4(),
        variants=_make_four_variants(),
    )
    assert len(results) == 4


@pytest.mark.asyncio
async def test_service_variant_numbers_are_1_to_4(tmp_path: Path):
    provider = MockImageProvider()
    svc = ImageGenerationService(provider=provider, cache_root=tmp_path)
    results = await svc.generate_variants(
        session_id=uuid.uuid4(),
        variants=_make_four_variants(),
    )
    numbers = {r.variant_number for r in results}
    assert numbers == {1, 2, 3, 4}


@pytest.mark.asyncio
async def test_service_styles_match_input(tmp_path: Path):
    provider = MockImageProvider()
    svc = ImageGenerationService(provider=provider, cache_root=tmp_path)
    results = await svc.generate_variants(
        session_id=uuid.uuid4(),
        variants=_make_four_variants(),
    )
    styles = {r.style for r in results}
    assert styles == {"illustration", "geometric", "watercolor", "minimalist"}


@pytest.mark.asyncio
async def test_service_all_succeed_with_mock(tmp_path: Path):
    provider = MockImageProvider()
    svc = ImageGenerationService(provider=provider, cache_root=tmp_path)
    results = await svc.generate_variants(
        session_id=uuid.uuid4(),
        variants=_make_four_variants(),
    )
    assert all(r.result.success for r in results)


@pytest.mark.asyncio
async def test_service_seeds_are_passed_through(tmp_path: Path):
    provider = MockImageProvider()
    svc = ImageGenerationService(provider=provider, cache_root=tmp_path)
    seeds = [10, 20, 30, 40]
    results = await svc.generate_variants(
        session_id=uuid.uuid4(),
        variants=_make_four_variants(),
        seeds=seeds,
    )
    result_seeds = [
        r.result.generation_seed for r in sorted(results, key=lambda r: r.variant_number)
    ]
    assert result_seeds == seeds


@pytest.mark.asyncio
async def test_service_raises_on_wrong_variant_count(tmp_path: Path):
    provider = MockImageProvider()
    svc = ImageGenerationService(provider=provider, cache_root=tmp_path)
    with pytest.raises(ValueError, match="Expected exactly 4"):
        await svc.generate_variants(
            session_id=uuid.uuid4(),
            variants=[_make_variant()],
        )


@pytest.mark.asyncio
async def test_service_provider_called_four_times(tmp_path: Path):
    provider = MockImageProvider()
    svc = ImageGenerationService(provider=provider, cache_root=tmp_path)
    await svc.generate_variants(
        session_id=uuid.uuid4(),
        variants=_make_four_variants(),
    )
    assert len(provider.calls) == 4


@pytest.mark.asyncio
async def test_service_handles_provider_exception_per_variant(tmp_path: Path):
    """A failing provider should produce an error result, not raise."""

    class BoomProvider:
        provider_name = "boom"

        async def generate(self, params, *, output_dir, variant_number, session_id):
            if variant_number == 2:
                raise RuntimeError("boom!")
            return GenerationResult(
                success=True,
                image_url="/cache/ok.png",
                image_path=str(tmp_path / "ok.png"),
                provider_request_id="ok",
                generation_seed=1,
                generation_time_ms=10,
                model_used="test",
                provider_name="boom",
            )

    svc = ImageGenerationService(provider=BoomProvider(), cache_root=tmp_path)
    results = await svc.generate_variants(
        session_id=uuid.uuid4(),
        variants=_make_four_variants(),
    )
    assert len(results) == 4
    failed = [r for r in results if r.variant_number == 2]
    assert len(failed) == 1
    assert failed[0].result.success is False
    assert "boom!" in failed[0].result.error
    # Other variants succeeded
    assert sum(1 for r in results if r.result.success) == 3
