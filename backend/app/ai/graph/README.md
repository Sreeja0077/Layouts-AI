# LangGraph StateGraph Workflows

## 📌 Purpose & Overview
Orchestrates AI multi-step reasoning workflows using LangGraph state graphs with persistent checkpointing.

## 🏗️ Phase 8 Requirement Workflow (`requirement_workflow.py`)
- **State Schema (`RequirementWorkflowState`)**: Carries `raw_text`, `requirement_set`, `needs_clarification`, `questions`, and `user_answer`.
- **Node Execution Flow**:
  1. `parse_node`: Invokes `RequirementParser` on raw text to produce initial `RequirementSet`.
  2. `evaluate_node`: Invokes deterministic completeness checklist. If resuming with `user_answer`, non-destructively merges the answer via `merge_clarification_answer`.
  3. `clarification_pause`: Pauses workflow when blocking questions remain (`CLARIFICATION_REQUIRED`).
  4. `finalize`: Completes and marks state as `NORMALIZED`.
- **State Checkpointing**: Uses `MemorySaver` keyed by `thread_id` (matching `requirement_set_id`) for turn-by-turn pause and resume.
