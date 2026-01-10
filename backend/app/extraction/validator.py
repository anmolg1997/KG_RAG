"""
Validation logic for extracted entities and relationships.

Ensures extraction results conform to the ontology schema and
contain valid, consistent data.
"""

import logging
from typing import Optional

from pydantic import ValidationError

from app.extraction.ontology import (
    ExtractedGraph,
    Contract,
    Party,
    Clause,
    Obligation,
    ContractDate,
    Amount,
    Relationship,
    RelationshipType,
    OntologyRegistry,
)

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of validation with detailed error information."""
    
    def __init__(self):
        self.is_valid = True
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.entity_errors: dict[str, list[str]] = {}
        self.relationship_errors: list[str] = []
    
    def add_error(self, error: str, entity_id: Optional[str] = None):
        """Add an error to the result."""
        self.is_valid = False
        self.errors.append(error)
        if entity_id:
            if entity_id not in self.entity_errors:
                self.entity_errors[entity_id] = []
            self.entity_errors[entity_id].append(error)
    
    def add_warning(self, warning: str):
        """Add a warning (doesn't invalidate result)."""
        self.warnings.append(warning)
    
    def add_relationship_error(self, error: str):
        """Add a relationship-specific error."""
        self.is_valid = False
        self.relationship_errors.append(error)
        self.errors.append(error)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "entity_errors": self.entity_errors,
            "relationship_errors": self.relationship_errors,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


class ExtractionValidator:
    """
    Validates extraction results against the ontology schema.
    
    Performs:
    - Schema validation (Pydantic)
    - Referential integrity checks
    - Business rule validation
    - Consistency checks
    """
    
    def __init__(self, strict: bool = False):
        """
        Initialize validator.
        
        Args:
            strict: If True, warnings become errors
        """
        self.strict = strict
        self.valid_relationship_types = set(RelationshipType.__members__.values())
    
    def validate(self, extracted: ExtractedGraph) -> ValidationResult:
        """
        Validate a complete extraction result.
        
        Args:
            extracted: The extraction result to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        
        # Collect all entity IDs for reference checking
        all_entity_ids = self._collect_entity_ids(extracted)
        
        # Validate each entity type
        self._validate_contracts(extracted.contracts, result)
        self._validate_parties(extracted.parties, result)
        self._validate_clauses(extracted.clauses, result)
        self._validate_obligations(extracted.obligations, all_entity_ids, result)
        self._validate_dates(extracted.dates, result)
        self._validate_amounts(extracted.amounts, result)
        
        # Validate relationships
        self._validate_relationships(extracted.relationships, all_entity_ids, result)
        
        # Cross-entity validation
        self._validate_cross_references(extracted, result)
        
        return result
    
    def _collect_entity_ids(self, extracted: ExtractedGraph) -> set[str]:
        """Collect all entity IDs from the extraction."""
        ids = set()
        
        for contract in extracted.contracts:
            ids.add(contract.id)
        for party in extracted.parties:
            ids.add(party.id)
        for clause in extracted.clauses:
            ids.add(clause.id)
        for obligation in extracted.obligations:
            ids.add(obligation.id)
        for date in extracted.dates:
            ids.add(date.id)
        for amount in extracted.amounts:
            ids.add(amount.id)
        
        return ids
    
    def _validate_contracts(
        self, contracts: list[Contract], result: ValidationResult
    ) -> None:
        """Validate contract entities."""
        if not contracts:
            result.add_warning("No contracts extracted from document")
            return
        
        for contract in contracts:
            # Title validation
            if not contract.title or len(contract.title) < 3:
                result.add_error(
                    f"Contract title too short: '{contract.title}'",
                    contract.id
                )
            
            # Date consistency
            if contract.effective_date and contract.expiration_date:
                if contract.effective_date > contract.expiration_date:
                    result.add_error(
                        "Effective date is after expiration date",
                        contract.id
                    )
            
            # Confidence check
            if contract.confidence < 0.6:
                result.add_warning(
                    f"Low confidence contract extraction: {contract.confidence}"
                )
    
    def _validate_parties(
        self, parties: list[Party], result: ValidationResult
    ) -> None:
        """Validate party entities."""
        if not parties:
            result.add_warning("No parties extracted from document")
            return
        
        seen_names = set()
        for party in parties:
            # Name validation
            if not party.name or len(party.name) < 2:
                result.add_error(
                    f"Party name too short: '{party.name}'",
                    party.id
                )
            
            # Duplicate check
            name_lower = party.name.lower().strip()
            if name_lower in seen_names:
                result.add_warning(f"Possible duplicate party: '{party.name}'")
            seen_names.add(name_lower)
    
    def _validate_clauses(
        self, clauses: list[Clause], result: ValidationResult
    ) -> None:
        """Validate clause entities."""
        for clause in clauses:
            # Text validation
            if not clause.text or len(clause.text) < 10:
                result.add_error(
                    f"Clause text too short (type: {clause.clause_type})",
                    clause.id
                )
            
            # Summary validation
            if not clause.summary or len(clause.summary) < 5:
                result.add_error(
                    f"Clause summary too short",
                    clause.id
                )
            
            # Summary should be shorter than text
            if len(clause.summary) > len(clause.text):
                result.add_warning(
                    f"Clause summary longer than text for {clause.id}"
                )
    
    def _validate_obligations(
        self,
        obligations: list[Obligation],
        all_entity_ids: set[str],
        result: ValidationResult,
    ) -> None:
        """Validate obligation entities."""
        for obligation in obligations:
            # Description validation
            if not obligation.description or len(obligation.description) < 10:
                result.add_error(
                    f"Obligation description too short",
                    obligation.id
                )
            
            # Party reference validation
            if obligation.obligor_id and obligation.obligor_id not in all_entity_ids:
                result.add_error(
                    f"Obligor ID references non-existent entity: {obligation.obligor_id}",
                    obligation.id
                )
            
            if obligation.obligee_id and obligation.obligee_id not in all_entity_ids:
                result.add_error(
                    f"Obligee ID references non-existent entity: {obligation.obligee_id}",
                    obligation.id
                )
    
    def _validate_dates(
        self, dates: list[ContractDate], result: ValidationResult
    ) -> None:
        """Validate date entities."""
        for date_entity in dates:
            # Must have either specific date or description
            if not date_entity.value and not date_entity.description:
                result.add_error(
                    "Date must have either value or description",
                    date_entity.id
                )
            
            # Relative date validation
            if date_entity.is_relative and not date_entity.relative_to:
                result.add_warning(
                    f"Relative date without relative_to: {date_entity.id}"
                )
    
    def _validate_amounts(
        self, amounts: list[Amount], result: ValidationResult
    ) -> None:
        """Validate amount entities."""
        for amount in amounts:
            # Must have description
            if not amount.description:
                result.add_error(
                    "Amount must have description",
                    amount.id
                )
            
            # Percentage validation
            if amount.is_percentage and amount.value is not None:
                if amount.value < 0 or amount.value > 100:
                    result.add_warning(
                        f"Percentage value out of range: {amount.value}%"
                    )
    
    def _validate_relationships(
        self,
        relationships: list[Relationship],
        all_entity_ids: set[str],
        result: ValidationResult,
    ) -> None:
        """Validate relationships."""
        seen_relationships = set()
        
        for rel in relationships:
            # Source entity exists
            if rel.source_id not in all_entity_ids:
                result.add_relationship_error(
                    f"Relationship source not found: {rel.source_id}"
                )
            
            # Target entity exists
            if rel.target_id not in all_entity_ids:
                result.add_relationship_error(
                    f"Relationship target not found: {rel.target_id}"
                )
            
            # Valid relationship type
            if rel.relationship_type not in [rt.value for rt in RelationshipType]:
                result.add_relationship_error(
                    f"Invalid relationship type: {rel.relationship_type}"
                )
            
            # Duplicate check
            rel_key = (rel.source_id, rel.target_id, rel.relationship_type)
            if rel_key in seen_relationships:
                result.add_warning(
                    f"Duplicate relationship: {rel.relationship_type} "
                    f"from {rel.source_id} to {rel.target_id}"
                )
            seen_relationships.add(rel_key)
    
    def _validate_cross_references(
        self, extracted: ExtractedGraph, result: ValidationResult
    ) -> None:
        """Validate cross-entity consistency."""
        # Check that contracts have parties
        if extracted.contracts and not extracted.parties:
            result.add_warning("Contract extracted but no parties found")
        
        # Check party-contract relationships exist
        party_ids = {p.id for p in extracted.parties}
        contract_ids = {c.id for c in extracted.contracts}
        
        has_party_rel = any(
            r.relationship_type == RelationshipType.HAS_PARTY.value
            for r in extracted.relationships
        )
        
        if party_ids and contract_ids and not has_party_rel:
            result.add_warning(
                "Parties and contracts extracted but no HAS_PARTY relationships"
            )
    
    def validate_entity(self, entity_type: str, data: dict) -> ValidationResult:
        """
        Validate a single entity against its schema.
        
        Args:
            entity_type: Name of entity type
            data: Entity data as dictionary
            
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        
        if entity_type not in OntologyRegistry.ENTITY_TYPES:
            result.add_error(f"Unknown entity type: {entity_type}")
            return result
        
        model_class = OntologyRegistry.ENTITY_TYPES[entity_type]
        
        try:
            model_class.model_validate(data)
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                result.add_error(f"{field}: {msg}")
        
        return result
