"""
Comprehensive Unit Tests for Phase 8: Requirement AI & Clarification Engine.
Tests all requirements without requiring an active LLM, network connection, or API keys.
"""

import json
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

_backend_root = str(Path(__file__).resolve().parent.parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from app.ai.graph.requirement_workflow import (
    build_requirement_workflow,
    merge_clarification_answer,
)
from app.ai.nodes.ambiguity_classifier import AmbiguityClassifier
from app.ai.nodes.requirement_parser import RequirementParser
from app.ai.providers.llm_provider import MockLLMProvider, set_active_llm_provider
from app.ai.schemas.structured_output import ParsedRequirementOutput
from app.domain.requirements.completeness import evaluate_requirement_completeness
from app.domain.requirements.schemas import (
    RequirementItem,
    RequirementSet,
    RequirementStatus,
    SpatialPreference,
)
from app.main import create_application


@pytest.fixture
def mock_provider():
    return MockLLMProvider()


@pytest.fixture
def parser(mock_provider):
    return RequirementParser(provider=mock_provider)


@pytest.fixture
def test_client():
    app = create_application()
    return TestClient(app)


# --------------------------------------------------------------------------
# Test 1: "10 seater conference room" -> conference semantic type + capacity 10
# --------------------------------------------------------------------------
def test_1_conference_room_with_capacity(parser):
    result = parser.parse(
        raw_text="Make this a 10 seater conference room",
        project_id="proj_1",
        floor_plan_id="fp_1",
    )
    assert len(result.items) >= 1
    assert result.items[0].semantic_type == "CONFERENCE_ROOM"
    assert result.target_density_seats == 10
    assert result.items[0].resolved_catalog_item_id is None
    assert result.items[0].resolution_method is None


# --------------------------------------------------------------------------
# Test 2: "6 professional desks" -> quantity 6 + semantic desk type
# --------------------------------------------------------------------------
def test_2_desks_with_quantity(parser):
    result = parser.parse(
        raw_text="Put 6 professional desks in this region",
        project_id="proj_1",
        floor_plan_id="fp_1",
    )
    assert len(result.items) >= 1
    item = result.items[0]
    assert item.semantic_type == "PROFESSIONAL_DESK"
    assert item.quantity == 6
    assert item.resolved_catalog_item_id is None
    assert item.dimensions_override is None


# --------------------------------------------------------------------------
# Test 3: "1 manager cabin near window" -> quantity 1 + manager cabin + near-window preference
# --------------------------------------------------------------------------
def test_3_manager_cabin_near_window(parser):
    result = parser.parse(
        raw_text="Place 1 manager cabin near the window",
        project_id="proj_1",
        floor_plan_id="fp_1",
    )
    assert len(result.items) >= 1
    assert result.items[0].semantic_type == "MANAGER_CABIN"
    assert result.items[0].quantity == 1
    assert len(result.preferences) >= 1
    assert result.preferences[0].preference_type == "NEAR_WINDOW"


# --------------------------------------------------------------------------
# Test 4: Missing quantity: "put desks here" -> clarification required
# --------------------------------------------------------------------------
def test_4_missing_quantity_triggers_clarification(parser):
    result = parser.parse(raw_text="put desks here")
    is_complete, questions, reasoning = evaluate_requirement_completeness(result)

    assert is_complete is False
    assert len(questions) >= 1
    assert any("quantity" in q.slot.lower() or "desk" in q.slot.lower() for q in questions)
    assert "quantity" in reasoning.lower() or "desk" in reasoning.lower()


# --------------------------------------------------------------------------
# Test 5: Missing capacity: "create conference room" -> clarification required
# --------------------------------------------------------------------------
def test_5_missing_capacity_triggers_clarification(parser):
    result = parser.parse(raw_text="create conference room here")
    is_complete, questions, reasoning = evaluate_requirement_completeness(result)

    assert is_complete is False
    assert len(questions) >= 1
    assert any("capacity" in q.slot.lower() for q in questions)
    assert "capacity" in reasoning.lower() or "seat" in reasoning.lower()


# --------------------------------------------------------------------------
# Test 6: Explicit region context: region_id is preserved in requirement state
# --------------------------------------------------------------------------
def test_6_region_id_preserved_in_state(parser):
    target_region_id = "reg_user_selected_999"
    result = parser.parse(
        raw_text="Make this a 10 seater conference room",
        project_id="proj_alpha",
        floor_plan_id="fp_beta",
        region_id=target_region_id,
    )
    assert result.room_id == target_region_id
    assert result.floor_plan_id == "fp_beta"
    assert result.project_id == "proj_alpha"


# --------------------------------------------------------------------------
# Test 7: No physical catalog resolution: resolved_catalog_item_id is None
# --------------------------------------------------------------------------
def test_7_no_physical_catalog_resolution(parser):
    result = parser.parse(raw_text="Place 6 executive desks and 1 manager cabin")
    for item in result.items:
        assert item.resolved_catalog_item_id is None, "Physical catalog resolution must remain None in Phase 8"
        assert item.resolution_method is None, "Resolution method must remain None in Phase 8"


# --------------------------------------------------------------------------
# Test 8: No invented dimensions: parser never produces unsupported dimensions
# --------------------------------------------------------------------------
def test_8_no_invented_dimensions(parser):
    result = parser.parse(raw_text="Put 4 professional desks here")
    for item in result.items:
        assert item.dimensions_override is None, "Dimensions must not be fabricated"


# --------------------------------------------------------------------------
# Test 9: Malformed LLM output -> Pydantic validation failure handled cleanly
# --------------------------------------------------------------------------
def test_9_malformed_llm_output_rejected():
    failing_provider = MockLLMProvider()
    failing_provider.register_response("bad request", "NOT_A_JSON_RESPONSE {{{")
    bad_parser = RequirementParser(provider=failing_provider)

    with pytest.raises(ValueError, match="Malformed LLM structured output"):
        bad_parser.parse("bad request")


# --------------------------------------------------------------------------
# Test 10: Low confidence ambiguity -> clarification request generated
# --------------------------------------------------------------------------
def test_10_low_confidence_ambiguity_triggers_clarification(parser):
    result = parser.parse(raw_text="Put a table here")
    classifier = AmbiguityClassifier()
    clarification_req = classifier.evaluate(result)

    assert clarification_req.needs_clarification is True
    assert len(clarification_req.questions) >= 1
    assert any("table" in q.slot.lower() for q in clarification_req.questions)


# --------------------------------------------------------------------------
# Test 11: Explicit complete requirement -> no unnecessary clarification
# --------------------------------------------------------------------------
def test_11_explicit_complete_requirement_no_clarification(parser):
    result = parser.parse(raw_text="Put 6 professional desks here")
    is_complete, questions, reasoning = evaluate_requirement_completeness(result)

    assert is_complete is True
    assert len(questions) == 0
    assert "complete" in reasoning.lower()


# --------------------------------------------------------------------------
# Test 12: Spatial preference extraction
# --------------------------------------------------------------------------
def test_12_spatial_preferences_extracted(parser):
    # Window preference
    res_win = parser.parse(raw_text="Put 4 executive desks near the window")
    assert any(p.preference_type == "NEAR_WINDOW" for p in res_win.preferences)

    # Perimeter preference
    res_perim = parser.parse(raw_text="Put 6 professional desks along the perimeter")
    assert any(p.preference_type == "ALONG_PERIMETER" for p in res_perim.preferences)

    # Entrance preference
    res_ent = parser.parse(raw_text="Put 4 desks near the entrance")
    assert any(p.preference_type == "NEAR_ENTRANCE" for p in res_ent.preferences)


# --------------------------------------------------------------------------
# Test 13: Multiple requirements captured
# --------------------------------------------------------------------------
def test_13_multiple_requirements_captured():
    multi_provider = MockLLMProvider()
    multi_provider.register_response(
        "complex_input",
        json.dumps({
            "summary": "Place 6 desks, 1 manager cabin, and a meeting room for 8.",
            "items": [
                {
                    "id": "req_1",
                    "raw_phrase": "6 desks",
                    "semantic_type": "PROFESSIONAL_DESK",
                    "resolved_catalog_item_id": None,
                    "resolution_method": None,
                    "confidence": 0.95,
                    "quantity": 6,
                    "slot_tags": ["desks"],
                    "dimensions_override": None
                },
                {
                    "id": "req_2",
                    "raw_phrase": "1 manager cabin",
                    "semantic_type": "MANAGER_CABIN",
                    "resolved_catalog_item_id": None,
                    "resolution_method": None,
                    "confidence": 0.95,
                    "quantity": 1,
                    "slot_tags": ["cabin"],
                    "dimensions_override": None
                },
                {
                    "id": "req_3",
                    "raw_phrase": "meeting room for 8",
                    "semantic_type": "MEETING_ROOM",
                    "resolved_catalog_item_id": None,
                    "resolution_method": None,
                    "confidence": 0.95,
                    "quantity": 1,
                    "slot_tags": ["meeting_room"],
                    "dimensions_override": None
                }
            ],
            "preferences": [],
            "target_density_seats": 15,
            "confidence_score": 0.95
        })
    )
    custom_parser = RequirementParser(provider=multi_provider)
    result = custom_parser.parse("complex_input")

    assert len(result.items) == 3
    semantic_types = [item.semantic_type for item in result.items]
    assert "PROFESSIONAL_DESK" in semantic_types
    assert "MANAGER_CABIN" in semantic_types
    assert "MEETING_ROOM" in semantic_types


# --------------------------------------------------------------------------
# Test 14: Natural-language variations normalize consistently
# --------------------------------------------------------------------------
def test_14_natural_language_variations_normalize_consistently(parser):
    phrasings = [
        "10 seater conference room",
        "ten seat conference room",
        "conference room for 10 people",
    ]
    for phrasing in phrasings:
        result = parser.parse(raw_text=phrasing)
        assert result.items[0].semantic_type == "CONFERENCE_ROOM"
        assert result.target_density_seats == 10


# --------------------------------------------------------------------------
# Test 15: Unknown physical term preserves raw phrase without hallucinating
# --------------------------------------------------------------------------
def test_15_unknown_term_preserves_raw_phrase():
    unknown_provider = MockLLMProvider()
    unknown_provider.register_response(
        "herman miller aeron",
        json.dumps({
            "summary": "Place Herman Miller Aeron ergonomic units",
            "items": [{
                "id": "req_item_1",
                "raw_phrase": "4 Herman Miller Aeron chairs",
                "semantic_type": "UNKNOWN_SEATING_PRODUCT",
                "resolved_catalog_item_id": None,
                "resolution_method": None,
                "confidence": 0.5,
                "quantity": 4,
                "slot_tags": ["ergonomic"],
                "dimensions_override": None
            }],
            "preferences": [],
            "target_density_seats": 4,
            "confidence_score": 0.5
        })
    )
    p = RequirementParser(provider=unknown_provider)
    res = p.parse("4 Herman Miller Aeron chairs")

    assert res.items[0].raw_phrase == "4 Herman Miller Aeron chairs"
    assert res.items[0].resolved_catalog_item_id is None, "Must not fabricate a catalog ID for unknown product"


# --------------------------------------------------------------------------
# Test 16: LangGraph pause and resume checkpointing workflow
# --------------------------------------------------------------------------
def test_16_langgraph_pause_and_resume_workflow():
    provider = MockLLMProvider()
    workflow = build_requirement_workflow(provider=provider)
    thread_id = "test_thread_phase_8_001"
    config = {"configurable": {"thread_id": thread_id}}

    # Initial submission: incomplete conference room (no capacity)
    state_1 = workflow.invoke(
        {"raw_text": "Create a conference room here"},
        config=config,
    )
    assert state_1["needs_clarification"] is True
    assert state_1["status"] == RequirementStatus.CLARIFICATION_REQUIRED.value
    assert len(state_1["questions"]) >= 1

    # Resume workflow with clarification answer "10"
    state_2 = workflow.invoke(
        {"user_answer": "10"},
        config=config,
    )
    assert state_2["needs_clarification"] is False
    assert state_2["status"] == RequirementStatus.NORMALIZED.value
    assert state_2["requirement_set"]["target_density_seats"] == 10
    assert state_2["requirement_set"]["items"][0]["semantic_type"] == "CONFERENCE_ROOM"


# --------------------------------------------------------------------------
# Test 17: Requirement API endpoints (FastAPI TestClient)
# --------------------------------------------------------------------------
def test_17_api_create_and_clarify_endpoints(test_client):
    set_active_llm_provider(MockLLMProvider())

    # 1. Complete requirement API call
    resp_complete = test_client.post(
        "/api/v1/requirements/",
        json={
            "raw_text": "Put 6 professional desks here",
            "project_id": "proj_101",
            "floor_plan_id": "fp_202",
        },
    )
    assert resp_complete.status_code == 201
    data_complete = resp_complete.json()
    assert data_complete["needs_clarification"] is False
    assert data_complete["status"] == "NORMALIZED"
    assert len(data_complete["requirement_set"]["items"]) >= 1
    assert data_complete["requirement_set"]["items"][0]["semantic_type"] == "PROFESSIONAL_DESK"

    # 2. Incomplete requirement API call requiring clarification
    resp_incomplete = test_client.post(
        "/api/v1/requirements/",
        json={
            "raw_text": "Create a conference room here",
            "project_id": "proj_101",
            "floor_plan_id": "fp_202",
        },
    )
    assert resp_incomplete.status_code == 201
    data_incomplete = resp_incomplete.json()
    assert data_incomplete["needs_clarification"] is True
    assert data_incomplete["status"] == "CLARIFICATION_REQUIRED"
    assert len(data_incomplete["questions"]) >= 1
    req_id = data_incomplete["requirement_set_id"]

    # 3. Clarification answer submission
    resp_clarify = test_client.post(
        f"/api/v1/requirements/{req_id}/clarify",
        json={"answer": "12 seats"},
    )
    assert resp_clarify.status_code == 200
    data_clarified = resp_clarify.json()
    assert data_clarified["needs_clarification"] is False
    assert data_clarified["status"] == "NORMALIZED"
    assert data_clarified["requirement_set"]["target_density_seats"] == 12

    # 4. Get requirement by ID
# --------------------------------------------------------------------------
# Test 18: Provider configuration selection (Real vs Mock)
# --------------------------------------------------------------------------
def test_18_provider_configuration_selection(monkeypatch):
    from app.ai.providers.llm_provider import get_llm_provider, LiteLLMProvider, MockLLMProvider, set_active_llm_provider

    set_active_llm_provider(None)
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    provider_mock = get_llm_provider()
    assert isinstance(provider_mock, MockLLMProvider)

    set_active_llm_provider(None)
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.delenv("OMA_MODEL_SPEC", raising=False)
    monkeypatch.delenv("OMA_MODEL_DEFAULT", raising=False)
    monkeypatch.setenv("LITELLM_MODEL_FAST", "ollama/llama3.2:3b")
    provider_real = get_llm_provider()
    assert isinstance(provider_real, LiteLLMProvider)
    assert provider_real.model_name == "ollama/llama3.2:3b"

    # Reset
    set_active_llm_provider(None)
    monkeypatch.setenv("USE_MOCK_LLM", "true")


# --------------------------------------------------------------------------
# Test 19: Real provider failure does NOT silently fall back to mock
# --------------------------------------------------------------------------
def test_19_real_provider_failure_surfaces_error(monkeypatch):
    from app.ai.providers.llm_provider import LiteLLMProvider
    import litellm

    real_provider = LiteLLMProvider(model_alias="llm_fast")

    def failing_completion(**kwargs):
        raise ConnectionError("Ollama daemon at localhost:11434 unreachable")

    monkeypatch.setattr(litellm, "completion", failing_completion)

    with pytest.raises(RuntimeError, match="Configured LLM provider failed"):
        real_provider.complete("Create a conference room")


# --------------------------------------------------------------------------
# Test 20: AmbiguityClassifier invokes LLM when deterministic checks pass
# --------------------------------------------------------------------------
def test_20_ambiguity_classifier_invokes_llm_when_complete():
    mock_prov = MockLLMProvider()
    mock_prov.register_response(
        "semantic ambiguity",
        json.dumps({
            "needs_clarification": False,
            "questions": [],
            "reasoning": "Semantic intent is fully clear."
        })
    )
    classifier = AmbiguityClassifier(provider=mock_prov)

    # 1. Complete requirement item (10 seats conference room)
    complete_req = RequirementSet(
        id="req_comp_1",
        project_id="p1",
        floor_plan_id="fp1",
        status=RequirementStatus.NORMALIZED,
        items=[
            RequirementItem(
                id="i1",
                raw_phrase="10 seater conference room",
                semantic_type="CONFERENCE_ROOM",
                quantity=1,
                confidence=0.95,
            )
        ],
        target_density_seats=10,
    )

    result = classifier.evaluate(complete_req)
    assert result.needs_clarification is False
    # Verify mock provider was actually invoked for semantic ambiguity evaluation
    assert any("semantic ambiguity" in inv["prompt"].lower() for inv in mock_prov.invocations)


# --------------------------------------------------------------------------
# Test 21: AmbiguityClassifier skips LLM when deterministic blocking triggers
# --------------------------------------------------------------------------
def test_21_ambiguity_classifier_skips_llm_on_deterministic_blocking():
    mock_prov = MockLLMProvider()
    classifier = AmbiguityClassifier(provider=mock_prov)

    # Incomplete conference room without seating capacity
    incomplete_req = RequirementSet(
        id="req_incomp_1",
        project_id="p1",
        floor_plan_id="fp1",
        status=RequirementStatus.DRAFT,
        items=[
            RequirementItem(
                id="i1",
                raw_phrase="create conference room",
                semantic_type="CONFERENCE_ROOM",
                quantity=1,
                confidence=0.95,
            )
        ],
        target_density_seats=None,
    )

    result = classifier.evaluate(incomplete_req)
    assert result.needs_clarification is True
    assert len(result.questions) >= 1
    # Verify LLM provider was NOT called because deterministic checks failed immediately
    assert len(mock_prov.invocations) == 0


# --------------------------------------------------------------------------
# Test 22: No unapproved default fallback values in completeness checks
# --------------------------------------------------------------------------
def test_22_no_unapproved_hardcoded_defaults():
    # Conference room without capacity
    conf_req = RequirementSet(
        id="req_conf",
        project_id="p1",
        floor_plan_id="fp1",
        status=RequirementStatus.DRAFT,
        items=[
            RequirementItem(
                id="i1",
                raw_phrase="conference room",
                semantic_type="CONFERENCE_ROOM",
                quantity=1,
                confidence=0.9,
            )
        ],
    )
    is_comp, questions, _ = evaluate_requirement_completeness(conf_req)
    assert is_comp is False
    assert len(questions) == 1
    # Must not contain hardcoded default fallback (must be None)
    assert questions[0].default_fallback_value is None
    # Suggested options should be empty by default (no unapproved corporate numbers)
    assert questions[0].suggested_options == []

    # Desks without quantity
    desk_req = RequirementSet(
        id="req_desk",
        project_id="p1",
        floor_plan_id="fp1",
        status=RequirementStatus.DRAFT,
        items=[
            RequirementItem(
                id="i2",
                raw_phrase="desks",
                semantic_type="PROFESSIONAL_DESK",
                quantity=0,
                confidence=0.7,
            )
        ],
    )
    is_comp_desk, questions_desk, _ = evaluate_requirement_completeness(desk_req)
    assert is_comp_desk is False
    assert questions_desk[0].default_fallback_value is None
    assert questions_desk[0].suggested_options == []


# --------------------------------------------------------------------------
# Test 23: Question ID based clarification resume locates exact slot
# --------------------------------------------------------------------------
def test_23_question_id_based_clarification_resume():
    provider = MockLLMProvider()
    workflow = build_requirement_workflow(provider=provider)
    thread_id = "test_thread_qid_resume_01"
    config = {"configurable": {"thread_id": thread_id}}

    # Initial state with missing capacity
    state_1 = workflow.invoke(
        {"raw_text": "Create a conference room"},
        config=config,
    )
    assert state_1["needs_clarification"] is True
    target_qid = state_1["questions"][0]["question_id"]

    # Resume by passing exact answered_question_id
    state_2 = workflow.invoke(
        {
            "user_answer": "12",
            "answered_question_id": target_qid,
        },
        config=config,
    )
    assert state_2["needs_clarification"] is False
    assert state_2["requirement_set"]["target_density_seats"] == 12


# --------------------------------------------------------------------------
# Test 24: Configurable checkpointer (Memory vs Postgres)
# --------------------------------------------------------------------------
def test_24_configurable_checkpointer(monkeypatch):
    from app.ai.graph.requirement_workflow import get_checkpointer, set_global_checkpointer
    from langgraph.checkpoint.memory import MemorySaver

    # 1. In-memory checkpointer
    set_global_checkpointer(None)
    monkeypatch.setenv("CHECKPOINT_BACKEND", "memory")
    cp_mem = get_checkpointer()
    assert isinstance(cp_mem, MemorySaver)

    # 2. Postgres checkpointer configuration attempt
    set_global_checkpointer(None)
    monkeypatch.setenv("CHECKPOINT_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://invalid_host:9999/dummy_db")
    with pytest.raises(RuntimeError, match="PostgreSQL checkpointer initialization failed"):
        get_checkpointer()

    # Reset
    set_global_checkpointer(None)
    monkeypatch.setenv("CHECKPOINT_BACKEND", "memory")


# --------------------------------------------------------------------------
# Test 25: API Error Semantics: provider failure returns 502
# --------------------------------------------------------------------------
def test_25_api_provider_failure_returns_502(test_client, monkeypatch):
    from app.ai.providers.llm_provider import LiteLLMProvider, set_active_llm_provider
    import litellm

    failing_provider = LiteLLMProvider(model_alias="llm_fast")

    def failing_completion(**kwargs):
        raise ConnectionError("Ollama daemon unreachable")

    monkeypatch.setattr(litellm, "completion", failing_completion)
    set_active_llm_provider(failing_provider)

    resp = test_client.post(
        "/api/v1/requirements/",
        json={"raw_text": "Create a conference room"},
    )
    assert resp.status_code == 502
    data = resp.json()
    assert "Configured LLM provider failed" in data["detail"]

    # Reset
    set_active_llm_provider(MockLLMProvider())


# --------------------------------------------------------------------------
# Fix Verification Tests (Targeted Bug Fix: Generic vs Specific, Multi-Item, Targeted Clarification)
# --------------------------------------------------------------------------

def test_target_fix_1_two_chairs_and_two_desks(parser):
    """
    TEST 1:
    Input: "2 chairs and 2 desks"
    Expected:
    2 RequirementItems:
    - CHAIR_GENERIC, quantity = 2
    - DESK_GENERIC, quantity = 2
    No PROFESSIONAL_DESK inference.
    No quantity = 0.
    No missing chair.
    Clarification must NOT ask for desk quantity.
    """
    result = parser.parse(raw_text="2 chairs and 2 desks")
    assert len(result.items) == 2, f"Expected 2 items, got {len(result.items)}"

    types = {item.semantic_type: item for item in result.items}
    assert "CHAIR_GENERIC" in types, "CHAIR_GENERIC missing"
    assert "DESK_GENERIC" in types, "DESK_GENERIC missing"
    assert "PROFESSIONAL_DESK" not in types, "PROFESSIONAL_DESK must not be inferred from generic desk"

    chair_item = types["CHAIR_GENERIC"]
    desk_item = types["DESK_GENERIC"]
    assert chair_item.quantity == 2, f"Expected chair quantity 2, got {chair_item.quantity}"
    assert desk_item.quantity == 2, f"Expected desk quantity 2, got {desk_item.quantity}"
    assert chair_item.resolved_catalog_item_id is None
    assert desk_item.resolved_catalog_item_id is None

    is_complete, questions, reasoning = evaluate_requirement_completeness(result)
    assert is_complete is False, "DESK_GENERIC must require desk_type clarification"
    assert len(questions) == 1
    q = questions[0]
    assert q.slot == "desk_type"
    assert "type" in q.question_text.lower()
    assert "how many" not in q.question_text.lower()
    assert q.item_id == desk_item.id


def test_target_fix_2_two_desks_asks_type_not_quantity(parser):
    """
    TEST 2:
    Input: "2 desks"
    Expected:
    semantic_type = DESK_GENERIC, quantity = 2
    needs_clarification = True
    question slot = desk_type
    question text asks which desk type, NOT quantity.
    """
    result = parser.parse(raw_text="2 desks")
    assert len(result.items) == 1
    item = result.items[0]
    assert item.semantic_type == "DESK_GENERIC"
    assert item.quantity == 2
    assert item.resolved_catalog_item_id is None

    is_complete, questions, reasoning = evaluate_requirement_completeness(result)
    assert is_complete is False
    assert len(questions) == 1
    q = questions[0]
    assert q.slot == "desk_type"
    assert "type" in q.question_text.lower()
    assert "how many" not in q.question_text.lower()
    assert q.item_id == item.id


def test_target_fix_3_two_professional_desks_no_clarification(parser):
    """
    TEST 3:
    Input: "2 professional desks"
    Expected:
    semantic_type = PROFESSIONAL_DESK, quantity = 2
    needs_clarification = False for desk type.
    """
    result = parser.parse(raw_text="2 professional desks")
    assert len(result.items) == 1
    item = result.items[0]
    assert item.semantic_type == "PROFESSIONAL_DESK"
    assert item.quantity == 2

    is_complete, questions, reasoning = evaluate_requirement_completeness(result)
    assert is_complete is True
    assert len(questions) == 0


def test_target_fix_4_two_executive_desks(parser):
    """
    TEST 4:
    Input: "2 executive desks"
    Expected:
    semantic_type = EXECUTIVE_DESK, quantity = 2
    """
    result = parser.parse(raw_text="2 executive desks")
    assert len(result.items) == 1
    item = result.items[0]
    assert item.semantic_type == "EXECUTIVE_DESK"
    assert item.quantity == 2

    is_complete, questions, _ = evaluate_requirement_completeness(result)
    assert is_complete is True
    assert len(questions) == 0


def test_target_fix_5_two_chairs_and_two_desks_word_numbers(parser):
    """
    TEST 5:
    Input: "two chairs and two desks"
    Expected:
    CHAIR_GENERIC x 2, DESK_GENERIC x 2
    """
    result = parser.parse(raw_text="two chairs and two desks")
    assert len(result.items) == 2
    types = {item.semantic_type: item for item in result.items}
    assert "CHAIR_GENERIC" in types
    assert "DESK_GENERIC" in types
    assert types["CHAIR_GENERIC"].quantity == 2
    assert types["DESK_GENERIC"].quantity == 2


def test_target_fix_6_six_professional_desks_and_one_manager_desk(parser):
    """
    TEST 6:
    Input: "6 professional desks and 1 manager desk"
    Expected:
    PROFESSIONAL_DESK x 6, MANAGER_DESK x 1 (two separate items)
    """
    result = parser.parse(raw_text="6 professional desks and 1 manager desk")
    assert len(result.items) == 2
    types = {item.semantic_type: item for item in result.items}
    assert "PROFESSIONAL_DESK" in types
    assert "MANAGER_DESK" in types
    assert types["PROFESSIONAL_DESK"].quantity == 6
    assert types["MANAGER_DESK"].quantity == 1


def test_target_fix_7_resume_workflow_updates_desk_type_and_preserves_quantity():
    """
    TEST 7:
    Input: "2 desks"
    Then answer: "Professional Desk"
    Expected:
    before: DESK_GENERIC x 2
    after: PROFESSIONAL_DESK x 2 (quantity remains 2)
    """
    provider = MockLLMProvider()
    workflow = build_requirement_workflow(provider=provider)
    thread_id = "test_target_fix_7_thread"
    config = {"configurable": {"thread_id": thread_id}}

    state_1 = workflow.invoke({"raw_text": "2 desks"}, config=config)
    assert state_1["needs_clarification"] is True
    req_items_1 = state_1["requirement_set"]["items"]
    assert len(req_items_1) == 1
    assert req_items_1[0]["semantic_type"] == "DESK_GENERIC"
    assert req_items_1[0]["quantity"] == 2
    q = state_1["questions"][0]
    assert q["slot"] == "desk_type"

    state_2 = workflow.invoke(
        {"user_answer": "Professional Desk", "answered_question_id": q["question_id"]},
        config=config,
    )
    assert state_2["needs_clarification"] is False
    assert state_2["status"] == RequirementStatus.NORMALIZED.value
    req_items_2 = state_2["requirement_set"]["items"]
    assert len(req_items_2) == 1
    assert req_items_2[0]["semantic_type"] == "PROFESSIONAL_DESK"
    assert req_items_2[0]["quantity"] == 2
    assert req_items_2[0]["resolved_catalog_item_id"] is None


def test_target_fix_8_multiple_clarification_targets():
    """
    TEST 8:
    Multiple clarification target test.
    Input: "2 chairs and 2 desks"
    If both chair and desk types require clarification, create two distinct questions.
    Answer the desk question.
    Expected:
    Only desk item changes. Chair item remains unchanged.
    """
    req_set = RequirementSet(
        id="req_multi_test",
        project_id="p1",
        floor_plan_id="fp1",
        status=RequirementStatus.CLARIFICATION_REQUIRED,
        items=[
            RequirementItem(
                id="req_item_chair",
                raw_phrase="2 chairs",
                semantic_type="CHAIR_GENERIC",
                quantity=2,
                confidence=0.95,
            ),
            RequirementItem(
                id="req_item_desk",
                raw_phrase="2 desks",
                semantic_type="DESK_GENERIC",
                quantity=2,
                confidence=0.95,
            ),
        ],
    )

    # Both chair and desk require clarification questions
    is_comp, questions, _ = evaluate_requirement_completeness(
        req_set,
        options_config={"require_chair_type": True},
    )
    assert is_comp is False
    assert len(questions) == 2
    desk_q = next(q for q in questions if q.slot == "desk_type")
    chair_q = next(q for q in questions if q.slot == "chair_type")
    assert desk_q.item_id == "req_item_desk"
    assert chair_q.item_id == "req_item_chair"

    # Answer ONLY the desk question
    updated_req_set = merge_clarification_answer(
        req_set=req_set,
        answer="Professional Desk",
        question_slot=desk_q.slot,
        target_item_id=desk_q.item_id,
    )

    items_map = {it.id: it for it in updated_req_set.items}
    # Desk changed to PROFESSIONAL_DESK, quantity 2
    assert items_map["req_item_desk"].semantic_type == "PROFESSIONAL_DESK"
    assert items_map["req_item_desk"].quantity == 2
    assert items_map["req_item_desk"].resolved_catalog_item_id is None
    # Chair remains CHAIR_GENERIC, quantity 2
    assert items_map["req_item_chair"].semantic_type == "CHAIR_GENERIC"
    assert items_map["req_item_chair"].quantity == 2
    assert items_map["req_item_chair"].resolved_catalog_item_id is None


def test_target_fix_9_no_quantity_hallucination(parser):
    """
    TEST 9:
    No quantity hallucination.
    Input: "desks" -> DESK_GENERIC, quantity = 0, quantity clarification allowed.
    But: "2 desks" must never result in quantity 0.
    """
    res_unspecified = parser.parse(raw_text="desks")
    assert res_unspecified.items[0].semantic_type == "DESK_GENERIC"
    assert res_unspecified.items[0].quantity == 0
    is_comp, questions, _ = evaluate_requirement_completeness(res_unspecified)
    assert is_comp is False
    assert any("quantity" in q.slot.lower() for q in questions)

    res_specified = parser.parse(raw_text="2 desks")
    assert res_specified.items[0].quantity == 2
    assert res_specified.items[0].quantity != 0


def test_target_fix_10_no_semantic_specificity_hallucination(parser):
    """
    TEST 10:
    No semantic specificity hallucination.
    Input: "desks" -> Must never produce PROFESSIONAL_DESK.
    Input: "chairs" -> Must never produce OFFICE_CHAIR.
    Input: "tables" -> Must never produce CONFERENCE_TABLE.
    """
    res_desk = parser.parse(raw_text="desks")
    assert res_desk.items[0].semantic_type == "DESK_GENERIC"
    assert res_desk.items[0].semantic_type != "PROFESSIONAL_DESK"

    res_chair = parser.parse(raw_text="chairs")
    assert res_chair.items[0].semantic_type == "CHAIR_GENERIC"
    assert res_chair.items[0].semantic_type != "OFFICE_CHAIR"

    res_table = parser.parse(raw_text="tables")
    assert res_table.items[0].semantic_type == "TABLE_GENERIC"
    assert res_table.items[0].semantic_type != "CONFERENCE_TABLE"


def test_missing_window_spatial_clarification(parser):
    """
    Test that requesting 'near the window' when architectural_context has windows_count=0
    triggers clarification asking where to position the items instead.
    """
    from app.domain.requirements.completeness import evaluate_requirement_completeness
    req_set = parser.parse(raw_text="6 Professional Desks + 1 Manager Cabin near the window")
    
    # 1. When windows exist (e.g. windows_count=3), requirement is complete
    is_complete, questions, reasoning = evaluate_requirement_completeness(
        req_set,
        architectural_context={"windows_count": 3},
    )
    assert is_complete is True
    assert len(questions) == 0

    # 2. When 0 windows exist (windows_count=0), triggers clarification
    is_complete_0, questions_0, reasoning_0 = evaluate_requirement_completeness(
        req_set,
        architectural_context={"windows_count": 0},
    )
    assert is_complete_0 is False
    assert len(questions_0) == 1
    assert questions_0[0].slot == "missing_window_alternative"
    assert "no windows" in questions_0[0].question_text.lower()
    assert "Near Entrance" in questions_0[0].suggested_options


def test_missing_window_clarification_resume_workflow(mock_provider):
    """
    Test full LangGraph pause and resume when window is missing,
    clarifying with 'Near Entrance' replaces the preference.
    """
    import uuid
    from app.ai.graph.requirement_workflow import get_requirement_workflow
    workflow = get_requirement_workflow(provider=mock_provider)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Initial state with windows_count=0
    state_1 = workflow.invoke(
        {
            "raw_text": "6 Professional Desks and 1 Manager Cabin near the window",
            "floor_plan_id": "fp_nowindows",
            "architectural_context": {"windows_count": 0},
        },
        config=config,
    )
    assert state_1["needs_clarification"] is True
    assert len(state_1["questions"]) == 1
    target_qid = state_1["questions"][0]["question_id"]
    assert state_1["questions"][0]["slot"] == "missing_window_alternative"

    # User answers 'Near Entrance'
    state_2 = workflow.invoke(
        {
            "user_answer": "Near Entrance",
            "answered_question_id": target_qid,
            "architectural_context": {"windows_count": 0},
        },
        config=config,
    )
    assert state_2["needs_clarification"] is False
    req = state_2["requirement_set"]
    # Verify preference was updated away from window to entrance
    assert any("entrance" in (p.get("target_zone") or "").lower() for p in req.get("preferences", []))
    assert not any("window" in (p.get("target_zone") or "").lower() for p in req.get("preferences", []))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

