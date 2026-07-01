"""TorenOne AI orchestration layer (Phase 3).

Server-side only.  Turns natural-language descriptions into a typed ``FrameSpec``,
asks clarifying questions, and drafts report narrative — using OpenAI ``gpt-5.5``.
The LLM never computes engineering numbers; the kernel does all arithmetic.
"""

from torenone_ai.clarify import (
    ClarifyingQuestion,
    clarification_prompt,
    clarifying_questions,
)
from torenone_ai.client import build_client, build_client_from_env
from torenone_ai.config import (
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_MODEL,
    AIConfig,
    MissingAPIKeyError,
)
from torenone_ai.design_agent import (
    AgentAction,
    AgentAlternative,
    AgentConstraints,
    AgentDesignOutcome,
    OpenAIProposer,
    run_design_agent,
)
from torenone_ai.narrative import (
    NarrativeError,
    NarrativeGuardError,
    NarrativeResult,
    assert_prose_has_no_literal_numbers,
    build_narrative_facts,
    deterministic_narrative,
    generate_narrative,
    render_narrative,
)
from torenone_ai.parsing import (
    Assumption,
    DrawingDecodeError,
    FrameSpecExtraction,
    MissingField,
    ParseResult,
    build_frame_spec,
    coerce_drawing_to_image_url,
    coerce_drawing_to_images,
    image_data_url,
    parse_description,
    parse_description_from_env,
    parse_drawing,
    pdf_to_image_data_url,
    pdf_to_image_data_urls,
    propose_frame_from_drawing,
)

__all__ = [
    "AIConfig",
    "MissingAPIKeyError",
    "DEFAULT_MODEL",
    "DEFAULT_FALLBACK_MODEL",
    "build_client",
    "build_client_from_env",
    # Spec parsing (Task 3.2)
    "FrameSpecExtraction",
    "ParseResult",
    "MissingField",
    "Assumption",
    "build_frame_spec",
    "parse_description",
    "parse_description_from_env",
    # Drawings/plans-in (vision)
    "parse_drawing",
    "propose_frame_from_drawing",
    "image_data_url",
    "pdf_to_image_data_url",
    "pdf_to_image_data_urls",
    "coerce_drawing_to_image_url",
    "coerce_drawing_to_images",
    "DrawingDecodeError",
    # Clarifying questions (Task 3.3)
    "ClarifyingQuestion",
    "clarifying_questions",
    "clarification_prompt",
    # Narrative generation (Task 3.4)
    "NarrativeResult",
    "NarrativeError",
    "NarrativeGuardError",
    "build_narrative_facts",
    "deterministic_narrative",
    "generate_narrative",
    "render_narrative",
    "assert_prose_has_no_literal_numbers",
    # Agentic design loop
    "AgentAction",
    "AgentAlternative",
    "AgentConstraints",
    "AgentDesignOutcome",
    "OpenAIProposer",
    "run_design_agent",
]
