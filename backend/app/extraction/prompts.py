"""
Prompt templates for entity and relationship extraction.

These prompts guide the LLM to extract structured information
from contract documents according to our ontology.
"""

from app.extraction.ontology import (
    ClauseType,
    PartyType,
    PartyRole,
    ObligationType,
    DateType,
)


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

EXTRACTION_SYSTEM_PROMPT = """You are an expert legal document analyst specializing in contract analysis and knowledge graph construction.

Your task is to extract structured information from contract documents and return it in a specific JSON format.

EXTRACTION PRINCIPLES:
1. Extract ONLY information explicitly stated in the text
2. Do not infer or assume information not present
3. Preserve exact quotes where relevant
4. Assign confidence scores based on clarity of information
5. Link entities through relationships when connections are explicit

CONFIDENCE SCORING:
- 1.0: Information is explicitly and clearly stated
- 0.8-0.9: Information is stated but requires some interpretation
- 0.6-0.7: Information is implied or partially stated
- Below 0.6: Do not extract (too uncertain)"""


# =============================================================================
# ENTITY EXTRACTION PROMPTS
# =============================================================================

PARTY_EXTRACTION_PROMPT = """Extract all parties mentioned in this contract text.

For each party, identify:
- name: Full legal name of the party
- type: One of {party_types}
- role: One of {party_roles}
- address: Physical address if mentioned
- jurisdiction: State/country of incorporation if mentioned

Contract Text:
{text}

Extract all parties as a JSON array.""".format(
    party_types=[pt.value for pt in PartyType],
    party_roles=[pr.value for pr in PartyRole],
    text="{text}",  # Placeholder for actual text
)


CLAUSE_EXTRACTION_PROMPT = """Extract and classify all clauses from this contract section.

For each clause, identify:
- clause_type: One of {clause_types}
- title: Section title if present
- section_number: Section/article number if present
- text: Full verbatim text of the clause
- summary: Brief 1-2 sentence summary
- key_terms: List of key legal terms or concepts

Contract Text:
{text}

Extract all clauses as a JSON array.""".format(
    clause_types=[ct.value for ct in ClauseType],
    text="{text}",
)


OBLIGATION_EXTRACTION_PROMPT = """Extract all obligations created by this contract text.

For each obligation, identify:
- obligation_type: One of {obligation_types}
- description: Clear description of what must be done
- conditions: Any conditions that must be met
- trigger_event: What triggers this obligation
- breach_consequences: Consequences of failing to fulfill

Also identify which party is the obligor (must perform) and which is the obligee (receives benefit).

Contract Text:
{text}

Extract all obligations as a JSON array.""".format(
    obligation_types=[ot.value for ot in ObligationType],
    text="{text}",
)


DATE_EXTRACTION_PROMPT = """Extract all significant dates from this contract text.

For each date, identify:
- date_type: One of {date_types}
- value: Specific date in YYYY-MM-DD format if available
- description: Description of the date or relative expression
- is_relative: Whether date is relative to an event (true/false)
- relative_to: If relative, what event it's relative to

Contract Text:
{text}

Extract all dates as a JSON array.""".format(
    date_types=[dt.value for dt in DateType],
    text="{text}",
)


AMOUNT_EXTRACTION_PROMPT = """Extract all monetary amounts from this contract text.

For each amount, identify:
- value: Numeric value (null if not specified)
- currency: Currency code (USD, EUR, etc.)
- description: Full context of the amount
- is_percentage: Whether this is a percentage (true/false)
- is_variable: Whether amount depends on conditions (true/false)
- formula: If calculated, the formula used

Contract Text:
{text}

Extract all amounts as a JSON array."""


# =============================================================================
# COMPREHENSIVE EXTRACTION PROMPT
# =============================================================================

FULL_EXTRACTION_PROMPT = """Analyze this contract document and extract a complete knowledge graph.

## ENTITY TYPES TO EXTRACT:

### 1. Contract (top-level)
- title: Name of the agreement
- contract_type: Type of contract (e.g., "License Agreement", "NDA", "Service Agreement")
- effective_date: When contract takes effect (YYYY-MM-DD)
- expiration_date: When contract ends (YYYY-MM-DD)
- summary: Brief executive summary

### 2. Parties
For each party:
- name: Full legal name
- type: {party_types}
- role: {party_roles}
- address: If mentioned
- jurisdiction: State/country of incorporation

### 3. Clauses
For each significant clause:
- clause_type: {clause_types}
- title: Section title
- section_number: Section/article number
- text: Full clause text (verbatim)
- summary: 1-2 sentence summary
- key_terms: List of key legal terms

### 4. Obligations
For each obligation:
- obligation_type: {obligation_types}
- description: What must be done
- conditions: Conditions that must be met
- trigger_event: What triggers the obligation
- breach_consequences: What happens if breached

### 5. Dates
For each significant date:
- date_type: {date_types}
- value: YYYY-MM-DD if specific
- description: Description or relative expression
- is_relative: true/false
- relative_to: Event if relative

### 6. Amounts
For each monetary amount:
- value: Numeric value
- currency: USD/EUR/GBP/etc.
- description: Context
- is_percentage: true/false
- is_variable: true/false

## RELATIONSHIPS TO EXTRACT:

- Contract HAS_PARTY Party
- Contract HAS_CLAUSE Clause
- Contract HAS_DATE ContractDate
- Clause CREATES_OBLIGATION Obligation
- Clause REFERENCES_AMOUNT Amount
- Clause REFERENCES_DATE ContractDate
- Obligation OBLIGATES Party (obligor)
- Obligation BENEFITS Party (obligee)
- Obligation HAS_DEADLINE ContractDate
- Clause RELATED_TO Clause

## CONTRACT DOCUMENT:

{text}

## OUTPUT FORMAT:

Return a JSON object with this structure:
{{
    "contracts": [...],
    "parties": [...],
    "clauses": [...],
    "obligations": [...],
    "dates": [...],
    "amounts": [...],
    "relationships": [
        {{
            "source_id": "<entity_id>",
            "target_id": "<entity_id>",
            "relationship_type": "<type>",
            "properties": {{}}
        }}
    ]
}}

Generate unique IDs for each entity and use them in relationships.""".format(
    party_types=[pt.value for pt in PartyType],
    party_roles=[pr.value for pr in PartyRole],
    clause_types=[ct.value for ct in ClauseType],
    obligation_types=[ot.value for ot in ObligationType],
    date_types=[dt.value for dt in DateType],
    text="{text}",
)


# =============================================================================
# CHUNK-LEVEL EXTRACTION PROMPT
# =============================================================================

CHUNK_EXTRACTION_PROMPT = """Analyze this chunk of a contract document and extract relevant entities.

This is chunk {chunk_index} of {total_chunks} from the document.

CONTEXT FROM PREVIOUS CHUNKS:
{context}

CURRENT CHUNK:
{text}

Extract entities following these guidelines:
1. Only extract entities clearly present in THIS chunk
2. Note references to entities from previous chunks
3. Mark cross-references with the original entity ID if known

Return a JSON object with:
- entities: New entities found in this chunk
- references: References to entities from previous chunks
- relationships: Relationships between entities"""


# =============================================================================
# VALIDATION PROMPT
# =============================================================================

VALIDATION_PROMPT = """Review this extracted knowledge graph for accuracy and completeness.

EXTRACTED DATA:
{extracted_data}

ORIGINAL TEXT:
{original_text}

Check for:
1. Accuracy: Do extracted facts match the source text?
2. Completeness: Are there important entities or relationships missing?
3. Consistency: Are there contradictions or duplicates?
4. Confidence: Are confidence scores appropriate?

Return a JSON object with:
{{
    "is_valid": true/false,
    "issues": ["list of issues found"],
    "suggestions": ["list of improvements"],
    "corrected_data": {{ ... }} // Only if corrections needed
}}"""


# =============================================================================
# QUERY UNDERSTANDING PROMPT
# =============================================================================

QUERY_DECOMPOSITION_PROMPT = """Analyze this user query about contract documents and decompose it into graph query components.

USER QUERY: {query}

Identify:
1. Intent: What is the user trying to find/understand?
2. Entity types: Which entity types are relevant? (Contract, Party, Clause, Obligation, Date, Amount)
3. Relationship types: Which relationships should be traversed?
4. Filters: Any specific conditions (dates, amounts, party names)?
5. Aggregations: Any counts, sums, or comparisons needed?

Return a JSON object:
{{
    "intent": "description of user intent",
    "entity_types": ["list of relevant types"],
    "relationship_types": ["list of relationships to traverse"],
    "filters": {{"field": "value"}},
    "aggregations": ["list of aggregations"],
    "cypher_hints": "suggested Cypher query patterns"
}}"""
