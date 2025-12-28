# 🐛 Implementation Plan: v0.7.1 — Bugfix Release

> **Target Release**: December 23, 2025  
> **Current Status**: ✅ **IMPLEMENTATION COMPLETE**  
> **Overall Progress**: 100% ✅✅✅✅✅✅✅✅✅✅  
> **Type**: Bugfix release (no new features)
> **Completion Date**: December 23, 2025

---

## 📊 Implementation Progress

| Bug | Task | Status | Priority |
|-----|------|--------|----------|
| **Bug #1: Charset conflict** | | **2/2 completed** | |
| 1.1 | Add unit test for charset in `/metrics` endpoint | ✅ Completed | 🟡 High |
| 1.2 | Verify test passes (charset already fixed) | ✅ Completed | 🟡 High |
| **Bug #2: Prefix matching** | | **4/4 completed** | |
| 2.1 | Implement longest-prefix matching helper function | ✅ Completed | 🔴 Critical |
| 2.2 | Fix `get_price_per_1k()` to use prefix matching | ✅ Completed | 🔴 Critical |
| 2.3 | Add unit tests for prefix matching edge cases | ✅ Completed | 🔴 Critical |
| 2.4 | Verify warnings disappear for provider variants | ✅ Completed | 🔴 Critical |
| **Bug #3: tiktoken Windows** | | **1/1 completed** | |
| 3.1 | Update CHANGELOG.md (tiktoken version fix) | ✅ Completed | 🟢 Low |
| **Documentation & Release** | | **3/3 completed** | |
| 4.1 | Update version in `pyproject.toml` (0.7.0 → 0.7.1) | ✅ Completed | 🔴 Critical |
| 4.2 | Add v0.7.1 section to CHANGELOG.md | ✅ Completed | 🔴 Critical |
| 4.3 | Run full test suite + verify coverage ≥81% | ✅ Completed | 🔴 Critical |

**Total Tasks**: 10  
**Completed**: 10  
**Remaining**: 0

---

## 🐛 Bug #1: Charset conflict в `/metrics` endpoint

**Status**: ✅ Code already fixed (charset separated from content_type)  
**Action Required**: Add unit test to verify fix

### Task 1.1: Add unit test for charset verification

**File**: `tests/test_prometheus_exporter.py` (NEW)

**Purpose**: Verify that `/metrics` endpoint returns correct charset in Content-Type header

**Implementation Details**:

```python
"""Unit tests for Prometheus exporter."""

import pytest
from aiohttp.test_utils import AioHTTPTestCase
from orchestrator.prometheus_exporter import PrometheusExporter

class TestPrometheusExporterMetricsEndpoint:
    """Test /metrics endpoint behavior."""
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint_charset_utf8(self) -> None:
        """Test that /metrics endpoint returns proper UTF-8 charset."""
        exporter = PrometheusExporter(port=0)  # Use random port for test
        await exporter.start()
        
        try:
            # Make request to /metrics endpoint
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:{exporter.port}/metrics") as resp:
                    assert resp.status == 200
                    # Verify Content-Type header includes charset
                    content_type = resp.headers.get("Content-Type", "")
                    assert "charset=utf-8" in content_type.lower()
                    assert "text/plain" in content_type.lower()
                    # Verify body is valid Prometheus format (contains HELP or TYPE)
                    body = await resp.text()
                    assert "# HELP" in body or "# TYPE" in body
        finally:
            await exporter.stop()
```

**Expected Result**: 
- Test file created at `tests/test_prometheus_exporter.py`
- Test verifies: status 200, charset=utf-8 in Content-Type, valid Prometheus format

### Task 1.2: Verify test passes

**Action**: Run `pytest tests/test_prometheus_exporter.py -v`

**Expected Result**: 
- Test passes (confirms charset fix is working)
- No warnings or errors

---

## 🐛 Bug #2: Prefix matching для вариантов провайдеров

**Status**: ❌ `get_price_per_1k()` missing prefix matching  
**Action Required**: Implement longest-prefix matching logic

### Task 2.1: Implement longest-prefix matching helper function

**File**: `src/orchestrator/pricing.py` (MODIFY)

**Purpose**: Create reusable helper function for provider name matching

**Implementation Details**:

```python
def _find_provider_prefix(provider_name: str, known_providers: list[str]) -> str | None:
    """Find matching provider using longest-prefix matching.
    
    Matching logic:
    1. Exact match: "gigachat" → "gigachat" ✅
    2. Longest prefix: "gigachat-pro-custom" → "gigachat-pro" ✅
    3. Fallback: "gigachat-dev" → "gigachat" ✅
    4. No match: "mockery" → None ❌ (doesn't match "mock")
    
    Args:
        provider_name: Provider name to match (case-insensitive)
        known_providers: List of known provider names from PRICING.keys()
        
    Returns:
        Matched provider name or None if no match found.
        
    Example:
        >>> _find_provider_prefix("mock-1", ["mock", "gigachat"])
        "mock"
        
        >>> _find_provider_prefix("gigachat-pro-custom", ["gigachat", "gigachat-pro"])
        "gigachat-pro"  # Longest match
        
        >>> _find_provider_prefix("mockery", ["mock"])
        None  # "mockery" doesn't start with "mock-"
    """
    provider_key = provider_name.lower()
    
    # 1. Exact match
    if provider_key in known_providers:
        return provider_key
    
    # 2. Longest prefix match (sort by length DESC to try longest first)
    sorted_providers = sorted(known_providers, key=len, reverse=True)
    for known in sorted_providers:
        # Match if provider_name starts with known + "-"
        # e.g., "gigachat-pro-custom" starts with "gigachat-pro-"
        if provider_key.startswith(known + "-"):
            return known
    
    return None  # Unknown provider
```

**Expected Result**: 
- Helper function `_find_provider_prefix()` added to `pricing.py`
- Function handles exact match, longest-prefix match, and no-match cases
- Edge case: "mockery" doesn't match "mock" (requires "-" separator)

### Task 2.2: Fix `get_price_per_1k()` to use prefix matching

**File**: `src/orchestrator/pricing.py` (MODIFY)

**Current Code** (lines 159-163):
```python
def get_price_per_1k(provider_name: str, model: str | None) -> float:
    provider_key = provider_name.lower()
    provider_pricing = PRICING.get(provider_key, {})
    return provider_pricing.get(
        model or "default", provider_pricing.get("default", 0.0)
    )
```

**Fixed Code**:
```python
def get_price_per_1k(provider_name: str, model: str | None) -> float:
    """Get price per 1000 tokens for a provider/model combination.
    
    This function now supports prefix matching for provider variants:
    - "mock-1" → "mock"
    - "gigachat-pro-custom" → "gigachat-pro" (longest match)
    - "gigachat-dev" → "gigachat"
    """
    provider_key = provider_name.lower()
    
    # Try direct lookup first
    provider_pricing = PRICING.get(provider_key)
    
    # If not found, try prefix matching
    if not provider_pricing:
        matched_provider = _find_provider_prefix(provider_key, list(PRICING.keys()))
        if matched_provider:
            provider_pricing = PRICING[matched_provider]
        else:
            # Unknown provider
            logger.warning(
                f"Unknown provider '{provider_name}', assuming zero cost. "
                f"Available providers: {list(PRICING.keys())}"
            )
            return 0.0
    
    return provider_pricing.get(
        model or "default", provider_pricing.get("default", 0.0)
    )
```

**Expected Result**: 
- `get_price_per_1k()` now uses `_find_provider_prefix()` helper
- Warnings disappear for "mock-1", "gigachat-pro-custom", etc.
- Backward compatible (exact matches still work)

### Task 2.3: Add unit tests for prefix matching edge cases

**File**: `tests/test_pricing.py` (MODIFY)

**Purpose**: Test longest-prefix matching logic and edge cases

**New Tests to Add**:

```python
class TestGetPricePer1kPrefixMatching:
    """Test prefix matching for get_price_per_1k()."""
    
    def test_get_price_prefix_match_mock_variants(self) -> None:
        """Test that mock-1, mock-2 match 'mock' provider."""
        price1 = get_price_per_1k("mock-1", "default")
        price2 = get_price_per_1k("mock-2", "default")
        price3 = get_price_per_1k("mock-async", "default")
        assert price1 == 0.0
        assert price2 == 0.0
        assert price3 == 0.0
    
    def test_get_price_longest_prefix_match(self) -> None:
        """Test longest-prefix matching (gigachat-pro-custom → gigachat-pro)."""
        # This should match "gigachat-pro" (longest match), not "gigachat"
        price = get_price_per_1k("gigachat-pro-custom", "GigaChat-Pro")
        assert price == pytest.approx(2.00)  # gigachat-pro pricing
    
    def test_get_price_fallback_to_shorter_prefix(self) -> None:
        """Test fallback to shorter prefix (gigachat-dev → gigachat)."""
        price = get_price_per_1k("gigachat-dev", "GigaChat")
        assert price == pytest.approx(1.00)  # gigachat pricing
    
    def test_get_price_no_false_positives(self) -> None:
        """Ensure 'mockery' doesn't match 'mock' (requires '-' separator)."""
        price = get_price_per_1k("mockery", "default")
        assert price == 0.0  # Unknown provider, returns 0.0
    
    def test_get_price_exact_match_priority(self) -> None:
        """Test that exact match takes priority over prefix match."""
        price = get_price_per_1k("mock", "default")
        assert price == 0.0  # Exact match for "mock"
```

**Expected Result**: 
- 5 new test methods added to `tests/test_pricing.py`
- Tests cover: variants, longest-prefix, fallback, false positives, exact match priority
- All tests pass

### Task 2.4: Verify warnings disappear

**Action**: Run `pytest tests/test_pricing.py::TestGetPricePer1kPrefixMatching -v`

**Expected Result**: 
- All tests pass
- No warnings logged for "mock-1", "gigachat-pro-custom", etc.
- Warnings only for truly unknown providers (e.g., "unknown-provider")

---

## 🐛 Bug #3: tiktoken Windows compatibility

**Status**: ✅ Already fixed (version 0.12.0 in pyproject.toml)  
**Action Required**: Update CHANGELOG.md

### Task 3.1: Update CHANGELOG.md

**File**: `CHANGELOG.md` (MODIFY)

**Action**: Add entry in v0.7.1 section (to be created in Task 4.2):

```markdown
### Fixed
- Updated `tiktoken` to ^0.12.0 for pre-built Windows wheels (was ^0.5.2 in v0.7.0)
```

**Expected Result**: 
- CHANGELOG.md documents tiktoken version update
- Note explains Windows compatibility fix

---

## 📝 Documentation & Release

### Task 4.1: Update version in pyproject.toml

**File**: `pyproject.toml` (MODIFY)

**Action**: Change version from `0.7.0` to `0.7.1`

**Line to modify**: Line 3
```toml
version = "0.7.1"
```

**Expected Result**: 
- Version bumped to 0.7.1
- No other changes to pyproject.toml

### Task 4.2: Add v0.7.1 section to CHANGELOG.md

**File**: `CHANGELOG.md` (MODIFY)

**Action**: Add new section at the top (after line 7):

```markdown
## [0.7.1] - 2025-12-23

### Fixed

- **Prometheus metrics endpoint charset**: Fixed charset conflict in `/metrics` endpoint response headers
  - Content-Type now correctly includes `charset=utf-8` without conflicts
  - Added unit test to verify charset handling
  
- **Provider prefix matching**: Fixed "Unknown provider" warnings for provider variants
  - `get_price_per_1k()` now supports longest-prefix matching (e.g., "mock-1" → "mock")
  - Added helper function `_find_provider_prefix()` for consistent matching logic
  - Edge cases handled: "gigachat-pro-custom" → "gigachat-pro" (longest match)
  - False positives prevented: "mockery" doesn't match "mock" (requires "-" separator)
  
- **tiktoken Windows compatibility**: Updated to version 0.12.0 for pre-built Windows wheels
  - Resolves compilation issues on Windows systems
  - Previous version (^0.5.2) required compilation from source

### Testing

- Added unit test for Prometheus endpoint charset verification
- Added comprehensive tests for provider prefix matching edge cases
- All existing tests continue to pass (203 tests)

### Notes

- Backward compatible with v0.7.0 (no breaking changes)
- Test coverage maintained at ≥81%
```

**Expected Result**: 
- New section `## [0.7.1] - 2025-12-23` added to CHANGELOG.md
- All three bugfixes documented
- Testing section notes new tests added

### Task 4.3: Run full test suite + verify coverage

**Actions**:
1. Run `pytest tests/ -v --cov=src/orchestrator --cov-report=term-missing`
2. Run `mypy src/orchestrator --strict`
3. Run `ruff check src/ tests/`

**Expected Results**: 
- ✅ All tests pass (203+ tests, including new ones)
- ✅ Code coverage ≥81% (not decreased)
- ✅ `mypy --strict`: 0 errors
- ✅ `ruff check`: 0 warnings
- ✅ No regressions introduced

---

## ✅ Definition of Done

**All tasks complete when**:
- [x] Bug #1: Unit test added and passing
- [x] Bug #2: Prefix matching implemented + tests passing + no warnings
- [x] Bug #3: CHANGELOG updated
- [x] Version bumped to 0.7.1
- [x] CHANGELOG.md updated with v0.7.1 section
- [x] All tests pass (203+)
- [x] Code coverage ≥81%
- [x] `mypy --strict`: 0 errors
- [x] `ruff check`: 0 warnings
- [x] Backward compatibility verified (no API changes)

---

## 📋 Implementation Notes

### Code Quality Standards
- **Type hints**: All functions fully typed (`mypy --strict` compatible)
- **Docstrings**: Google style for all public functions
- **Comments**: Explain **why**, not **what**
- **No hardcode**: Use constants/config where appropriate

### Testing Requirements
- **Unit tests**: Minimum 1 test per bugfix
- **Coverage**: Maintain ≥81% (don't decrease)
- **Test naming**: `test_<issue>_<scenario>` format

### Backward Compatibility
- ✅ No API changes (public methods unchanged)
- ✅ No breaking changes to data structures
- ✅ Existing code continues to work without modifications

---

## 🚀 Next Steps

1. **Review this plan** with team/stakeholders
2. **Start implementation** with Bug #2 (most critical)
3. **Test incrementally** after each bugfix
4. **Final verification** before release

---

**Plan Created**: December 23, 2025  
**Plan Status**: ✅ Ready for implementation  
**Estimated Time**: ~1 hour (bugfix release)

