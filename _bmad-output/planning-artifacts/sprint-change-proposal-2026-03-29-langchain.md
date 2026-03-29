# Sprint Change Proposal — Remove LangChain Dependency

**Date:** 2026-03-29
**Scope:** Minor — Direct implementation by development team
**Status:** Approved

---

## Section 1: Issue Summary

**Problem statement:** The `langchain-core` package is listed as a production dependency but is used solely for two data-structure / function-composition primitives: `Document` (a named container with `page_content` and `metadata` fields) and `RunnableLambda` (a thin wrapper that allows functions to be composed with the `|` operator). No LangChain-specific capabilities are exercised — no LLM calls, agent loops, tool use, callbacks, or distributed tracing.

**Discovery context:** Identified during proactive dependency review on Epic 4. The architecture document originally described LangChain as a learning objective; that goal has now been served and the dependency no longer earns its place.

**Evidence:**
- LangChain imports appear only in `backend/app/adapters/google_cloud_vision_ocr_provider.py` and `backend/app/adapters/textract_ocr_provider.py`.
- No references in `services/`, `core/`, `api/`, `schemas/`, or `middleware/`.
- The extraction chain in each file reduces to: `return _documents_to_segments(_gcv_response_to_documents(response))`

---

## Section 2: Impact Analysis

**Epic Impact:**
- Epic 4 (in progress): no in-progress story affected.
- Epic 3 (complete): FR25 text references "LangChain/tool execution trace data" — the qualifier "LangChain/" becomes a misnomer and is removed. The trace data itself is unaffected.
- Epics 1, 2, 5: unaffected.

**Story Impact:**
- No story acceptance criteria change.
- FR25 wording update in `epics.md`.

**Artifact Conflicts:**
- `architecture.md`: remove the sentence describing LangChain as a "core implementation goal and learning objective"; replace with a description of the simple functional pipeline pattern.
- `epics.md` FR25: remove "LangChain/" qualifier.

**Technical Impact:**
- `backend/pyproject.toml`: remove `langchain-core==0.3.81`
- `backend/uv.lock`: regenerate
- `backend/app/adapters/google_cloud_vision_ocr_provider.py`: replace `Document` + `RunnableLambda` with local dataclass + direct function call
- `backend/app/adapters/textract_ocr_provider.py`: same
- `backend/tests/unit/adapters/test_gcv_ocr_provider.py`: replace `Document` import
- `backend/tests/unit/adapters/test_textract_ocr_provider.py`: rename/rewrite `test_langchain_chain_invoked_with_full_response`

---

## Section 3: Recommended Approach

**Direct Adjustment (Option 1)**

Replace LangChain primitives with standard Python:
- `Document(page_content=x, metadata=d)` → local `@dataclass _OcrDoc(page_content: str, metadata: dict)`
- `RunnableLambda(f) | RunnableLambda(g)` → `g(f(x))`

No API contracts, response envelopes, or public interfaces change. All existing test assertions remain valid; only the test for the chain object itself is rewritten.

**Effort:** Low | **Risk:** Low | **Timeline impact:** None

---

## Section 4: Detailed Change Proposals

### Change 1 — `google_cloud_vision_ocr_provider.py`

Remove LangChain imports; add local `_OcrDoc` dataclass; replace chain with direct call.

```
OLD:
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
...
_extraction_chain = (
    RunnableLambda(_gcv_response_to_documents)
    | RunnableLambda(_documents_to_segments)
)
...
return _extraction_chain.invoke(response)

NEW:
@dataclasses.dataclass
class _OcrDoc:
    page_content: str
    metadata: dict
...
return _documents_to_segments(_gcv_response_to_documents(response))
```

### Change 2 — `textract_ocr_provider.py`

Same substitution as Change 1.

### Change 3 — `test_gcv_ocr_provider.py`

Replace `from langchain_core.documents import Document` with import of `_OcrDoc` from the provider module.

### Change 4 — `test_textract_ocr_provider.py`

```
OLD test name: test_langchain_chain_invoked_with_full_response
OLD: patches _extraction_chain and asserts .invoke() is called

NEW test name: test_extract_passes_full_response_dict_to_pipeline
NEW: patches the two transformation functions directly and asserts the correct
     response dict flows through, without depending on a chain object
```

### Change 5 — `pyproject.toml`

Remove `"langchain-core==0.3.81"` from `dependencies`.

### Change 6 — `architecture.md`

```
OLD: "The architecture must support LangChain-based orchestration as a core
     implementation goal and learning objective."

NEW: "The OCR adapter layer uses a simple functional pipeline — raw provider
     responses are transformed to normalised RawOcrSegment values through two
     composed pure functions, keeping provider-specific logic isolated from the
     service layer."
```

### Change 7 — `epics.md` FR25

```
OLD: FR25: System can expose LangChain/tool execution trace data for debugging.
NEW: FR25: System can expose tool execution trace data for debugging.
```

---

## Section 5: Implementation Handoff

**Scope:** Minor — development team implements directly.

**Success criteria:**
- `langchain-core` removed from `pyproject.toml` and `uv.lock`
- All backend tests pass (`pytest`)
- Linter passes (`ruff check`)
- No `langchain` imports remain in production code
