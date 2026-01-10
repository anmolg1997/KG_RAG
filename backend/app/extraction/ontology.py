"""
Ontology schema for Knowledge Graph extraction.

This module defines the structured schema for entities and relationships
that can be extracted from documents. The schema is designed for legal
contracts (CUAD dataset) but can be extended for other document types.

Ontology Design Principles:
1. Clear entity boundaries - each entity type has distinct properties
2. Explicit relationships - all connections are typed and directional
3. Validation constraints - Pydantic enforces data quality
4. Extensibility - easy to add new entity/relationship types
"""

from datetime import date
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ENUMERATIONS
# =============================================================================


class PartyType(str, Enum):
    """Types of parties in a contract."""
    INDIVIDUAL = "individual"
    CORPORATION = "corporation"
    LLC = "llc"
    PARTNERSHIP = "partnership"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"
    OTHER = "other"


class PartyRole(str, Enum):
    """Role of a party in the contract."""
    BUYER = "buyer"
    SELLER = "seller"
    LICENSOR = "licensor"
    LICENSEE = "licensee"
    LANDLORD = "landlord"
    TENANT = "tenant"
    EMPLOYER = "employer"
    EMPLOYEE = "employee"
    SERVICE_PROVIDER = "service_provider"
    CLIENT = "client"
    LENDER = "lender"
    BORROWER = "borrower"
    GUARANTOR = "guarantor"
    OTHER = "other"


class ClauseType(str, Enum):
    """
    Types of clauses commonly found in contracts.
    Based on CUAD dataset categories.
    """
    # Core Terms
    PARTIES = "parties"
    EFFECTIVE_DATE = "effective_date"
    TERM_DURATION = "term_duration"
    RENEWAL = "renewal"
    TERMINATION = "termination"
    
    # Financial
    PAYMENT = "payment"
    PRICE = "price"
    REVENUE_SHARING = "revenue_sharing"
    AUDIT_RIGHTS = "audit_rights"
    
    # Obligations
    DELIVERY = "delivery"
    PERFORMANCE = "performance"
    MINIMUM_COMMITMENT = "minimum_commitment"
    EXCLUSIVITY = "exclusivity"
    NON_COMPETE = "non_compete"
    
    # IP & Confidentiality
    INTELLECTUAL_PROPERTY = "intellectual_property"
    LICENSE_GRANT = "license_grant"
    CONFIDENTIALITY = "confidentiality"
    NON_DISCLOSURE = "non_disclosure"
    
    # Risk & Liability
    INDEMNIFICATION = "indemnification"
    LIABILITY_LIMITATION = "liability_limitation"
    WARRANTY = "warranty"
    INSURANCE = "insurance"
    
    # Dispute & Governance
    GOVERNING_LAW = "governing_law"
    DISPUTE_RESOLUTION = "dispute_resolution"
    ARBITRATION = "arbitration"
    JURISDICTION = "jurisdiction"
    
    # Change & Transfer
    ASSIGNMENT = "assignment"
    CHANGE_OF_CONTROL = "change_of_control"
    AMENDMENT = "amendment"
    
    # Miscellaneous
    FORCE_MAJEURE = "force_majeure"
    NOTICE = "notice"
    SEVERABILITY = "severability"
    ENTIRE_AGREEMENT = "entire_agreement"
    OTHER = "other"


class ObligationType(str, Enum):
    """Types of obligations that can arise from clauses."""
    PAYMENT = "payment"
    DELIVERY = "delivery"
    PERFORMANCE = "performance"
    NOTIFICATION = "notification"
    COMPLIANCE = "compliance"
    CONFIDENTIALITY = "confidentiality"
    INDEMNIFICATION = "indemnification"
    INSURANCE = "insurance"
    REPORTING = "reporting"
    OTHER = "other"


class ObligationStatus(str, Enum):
    """Status of an obligation."""
    ACTIVE = "active"
    PENDING = "pending"
    FULFILLED = "fulfilled"
    BREACHED = "breached"
    WAIVED = "waived"
    EXPIRED = "expired"


class DateType(str, Enum):
    """Types of dates in a contract."""
    EFFECTIVE_DATE = "effective_date"
    EXPIRATION_DATE = "expiration_date"
    TERMINATION_DATE = "termination_date"
    DEADLINE = "deadline"
    RENEWAL_DATE = "renewal_date"
    SIGNATURE_DATE = "signature_date"
    DELIVERY_DATE = "delivery_date"
    PAYMENT_DUE = "payment_due"
    OTHER = "other"


class Currency(str, Enum):
    """Common currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CNY = "CNY"
    INR = "INR"
    OTHER = "other"


# =============================================================================
# BASE ENTITY
# =============================================================================


class BaseEntity(BaseModel):
    """Base class for all entities with common fields."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score (0-1)"
    )
    source_text: Optional[str] = Field(
        default=None,
        description="Original text from which entity was extracted"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata"
    )


# =============================================================================
# ENTITY DEFINITIONS
# =============================================================================


class Party(BaseEntity):
    """
    A party (person or organization) in a contract.
    
    Examples:
        - "Acme Corporation" (corporation, seller)
        - "John Smith" (individual, buyer)
    """
    
    name: str = Field(..., description="Full legal name of the party")
    type: PartyType = Field(default=PartyType.OTHER)
    role: PartyRole = Field(default=PartyRole.OTHER)
    
    # Optional details
    address: Optional[str] = Field(default=None)
    jurisdiction: Optional[str] = Field(default=None, description="State/country of incorporation")
    registration_number: Optional[str] = Field(default=None, description="Company registration number")
    
    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Party name cannot be empty")
        return v.strip()


class ContractDate(BaseEntity):
    """
    A significant date in a contract.
    
    Examples:
        - Effective date: "January 1, 2024"
        - Termination deadline: "30 days after notice"
    """
    
    date_type: DateType = Field(..., description="Type of date")
    value: Optional[date] = Field(default=None, description="Specific date if known")
    description: str = Field(..., description="Description or relative date expression")
    
    # For relative dates
    is_relative: bool = Field(default=False, description="Whether date is relative to an event")
    relative_to: Optional[str] = Field(default=None, description="Event this date is relative to")


class Amount(BaseEntity):
    """
    A monetary amount mentioned in a contract.
    
    Examples:
        - "$1,000,000 annual license fee"
        - "5% of gross revenue"
    """
    
    value: Optional[float] = Field(default=None, description="Numeric value if specified")
    currency: Currency = Field(default=Currency.USD)
    description: str = Field(..., description="Full description of the amount")
    
    # For percentages or variable amounts
    is_percentage: bool = Field(default=False)
    is_variable: bool = Field(default=False, description="Whether amount depends on conditions")
    formula: Optional[str] = Field(default=None, description="Formula if amount is calculated")


class Clause(BaseEntity):
    """
    A clause or section in a contract.
    
    Clauses contain the substantive terms and may create obligations.
    
    Examples:
        - Section 5.1 Confidentiality
        - Article III - Payment Terms
    """
    
    clause_type: ClauseType = Field(..., description="Type of clause")
    title: Optional[str] = Field(default=None, description="Section title if present")
    section_number: Optional[str] = Field(default=None, description="Section/article number")
    text: str = Field(..., description="Full text of the clause")
    summary: str = Field(..., description="Brief summary of clause content")
    
    # Key provisions extracted
    key_terms: list[str] = Field(default_factory=list, description="Key terms/concepts")
    
    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Clause text cannot be empty")
        return v.strip()


class Obligation(BaseEntity):
    """
    An obligation arising from a contract clause.
    
    Obligations are actionable duties that one party owes to another.
    
    Examples:
        - "Buyer shall pay $10,000 within 30 days"
        - "Seller must maintain insurance coverage"
    """
    
    obligation_type: ObligationType = Field(..., description="Type of obligation")
    description: str = Field(..., description="Description of the obligation")
    status: ObligationStatus = Field(default=ObligationStatus.ACTIVE)
    
    # Parties involved
    obligor_id: Optional[str] = Field(default=None, description="ID of party who owes the obligation")
    obligee_id: Optional[str] = Field(default=None, description="ID of party to whom obligation is owed")
    
    # Conditions and triggers
    conditions: list[str] = Field(default_factory=list, description="Conditions for obligation")
    trigger_event: Optional[str] = Field(default=None, description="Event that triggers obligation")
    
    # Consequences
    breach_consequences: Optional[str] = Field(default=None, description="Consequences of breach")


class Contract(BaseEntity):
    """
    The top-level contract entity.
    
    Represents the overall agreement and contains references to all
    related entities.
    """
    
    title: str = Field(..., description="Contract title or name")
    contract_type: Optional[str] = Field(default=None, description="Type of contract")
    
    # Dates
    effective_date: Optional[date] = Field(default=None)
    expiration_date: Optional[date] = Field(default=None)
    
    # Status
    status: str = Field(default="active")
    
    # Summary
    summary: Optional[str] = Field(default=None, description="Executive summary of the contract")
    
    # Document source
    source_file: Optional[str] = Field(default=None, description="Source document filename")
    
    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Contract title cannot be empty")
        return v.strip()


# =============================================================================
# RELATIONSHIP DEFINITIONS
# =============================================================================


class Relationship(BaseModel):
    """
    A relationship between two entities in the knowledge graph.
    
    Relationships are directional: source -> target
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str = Field(..., description="ID of source entity")
    target_id: str = Field(..., description="ID of target entity")
    relationship_type: str = Field(..., description="Type of relationship")
    
    # Optional properties
    properties: dict = Field(default_factory=dict, description="Relationship properties")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class RelationshipType(str, Enum):
    """Standard relationship types in the ontology."""
    
    # Contract relationships
    HAS_PARTY = "HAS_PARTY"
    HAS_CLAUSE = "HAS_CLAUSE"
    HAS_DATE = "HAS_DATE"
    HAS_AMOUNT = "HAS_AMOUNT"
    
    # Clause relationships
    CREATES_OBLIGATION = "CREATES_OBLIGATION"
    REFERENCES_AMOUNT = "REFERENCES_AMOUNT"
    REFERENCES_DATE = "REFERENCES_DATE"
    RELATED_TO = "RELATED_TO"  # Between clauses
    
    # Obligation relationships
    OBLIGATES = "OBLIGATES"  # Obligation -> Party (obligor)
    BENEFITS = "BENEFITS"  # Obligation -> Party (obligee)
    HAS_DEADLINE = "HAS_DEADLINE"
    
    # Party relationships
    BETWEEN_PARTIES = "BETWEEN_PARTIES"


# =============================================================================
# EXTRACTION OUTPUT
# =============================================================================


class ExtractedGraph(BaseModel):
    """
    Complete extraction result containing all entities and relationships.
    
    This is the output of the extraction pipeline and input to the
    graph repository for storage.
    """
    
    # Source information
    source_document: str = Field(..., description="Source document identifier")
    extraction_model: str = Field(..., description="Model used for extraction")
    
    # Entities
    contracts: list[Contract] = Field(default_factory=list)
    parties: list[Party] = Field(default_factory=list)
    clauses: list[Clause] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    dates: list[ContractDate] = Field(default_factory=list)
    amounts: list[Amount] = Field(default_factory=list)
    
    # Relationships
    relationships: list[Relationship] = Field(default_factory=list)
    
    # Metadata
    extraction_metadata: dict = Field(default_factory=dict)
    
    @property
    def entity_count(self) -> int:
        """Total number of entities extracted."""
        return (
            len(self.contracts)
            + len(self.parties)
            + len(self.clauses)
            + len(self.obligations)
            + len(self.dates)
            + len(self.amounts)
        )
    
    @property
    def relationship_count(self) -> int:
        """Total number of relationships extracted."""
        return len(self.relationships)


# =============================================================================
# ONTOLOGY REGISTRY
# =============================================================================


class OntologyRegistry:
    """
    Registry of all entity and relationship types.
    
    Used for:
    - Generating extraction prompts
    - Validating extraction results
    - Building graph schema
    """
    
    ENTITY_TYPES = {
        "Contract": Contract,
        "Party": Party,
        "Clause": Clause,
        "Obligation": Obligation,
        "ContractDate": ContractDate,
        "Amount": Amount,
    }
    
    RELATIONSHIP_TYPES = [rt.value for rt in RelationshipType]
    
    @classmethod
    def get_entity_schema(cls, entity_type: str) -> dict:
        """Get JSON schema for an entity type."""
        if entity_type not in cls.ENTITY_TYPES:
            raise ValueError(f"Unknown entity type: {entity_type}")
        return cls.ENTITY_TYPES[entity_type].model_json_schema()
    
    @classmethod
    def get_all_schemas(cls) -> dict:
        """Get JSON schemas for all entity types."""
        return {
            name: model.model_json_schema()
            for name, model in cls.ENTITY_TYPES.items()
        }
    
    @classmethod
    def get_ontology_description(cls) -> str:
        """Get human-readable description of the ontology."""
        lines = ["# Contract Ontology\n"]
        
        lines.append("## Entity Types\n")
        for name, model in cls.ENTITY_TYPES.items():
            doc = model.__doc__ or "No description"
            lines.append(f"### {name}\n{doc.strip()}\n")
        
        lines.append("\n## Relationship Types\n")
        for rel_type in cls.RELATIONSHIP_TYPES:
            lines.append(f"- {rel_type}")
        
        return "\n".join(lines)
