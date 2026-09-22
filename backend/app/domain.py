"""Domain vocabulary: entity types, relation types, and job/answer enums.

This is the single source of truth for the GraphIntel ontology. Extraction,
graph writes, retrieval, and the frontend all reference these constants so the
knowledge graph stays internally consistent.
"""
from __future__ import annotations

from enum import Enum


class EntityType(str, Enum):
    CUSTOMER = "Customer"
    SUPPORT_TICKET = "SupportTicket"
    INCIDENT = "Incident"
    INCIDENT_UPDATE = "IncidentUpdate"
    POSTMORTEM = "Postmortem"
    RUNBOOK = "Runbook"
    SERVICE = "Service"
    TEAM = "Team"
    SLA_CONTRACT = "SLAContract"
    SLA_CLAUSE = "SLAClause"
    ERROR_SIGNATURE = "ErrorSignature"
    ROOT_CAUSE = "RootCause"
    DOCUMENT = "Document"
    CHUNK = "Chunk"
    EVIDENCE = "Evidence"


class RelationType(str, Enum):
    REPORTED = "REPORTED"                # Customer -> SupportTicket
    RELATED_TO = "RELATED_TO"            # SupportTicket -> Incident
    AFFECTED = "AFFECTED"                # Incident -> Service
    OWNED_BY = "OWNED_BY"                # Service -> Team
    CAUSED_BY = "CAUSED_BY"              # Incident -> RootCause
    HAS_UPDATE = "HAS_UPDATE"            # Incident -> IncidentUpdate
    HAS_CHUNK = "HAS_CHUNK"              # Document -> Chunk
    MENTIONS = "MENTIONS"                # Chunk -> Entity
    APPLIES_TO = "APPLIES_TO"            # SLAContract -> Customer
    PART_OF = "PART_OF"                  # SLAClause -> SLAContract
    CONSTRAINS = "CONSTRAINS"            # SLAClause -> Service
    MAY_VIOLATE = "MAY_VIOLATE"          # Incident -> SLAClause
    MITIGATES = "MITIGATES"              # Runbook -> ErrorSignature
    ANALYZES = "ANALYZES"                # Postmortem -> Incident
    EXHIBITS = "EXHIBITS"                # Incident/Ticket -> ErrorSignature


# Allowed (subject_type, object_type) pairs per relation. A relation may permit
# several endpoint shapes (e.g. both incidents and tickets EXHIBIT errors). Used
# to validate graph writes so extraction can never violate the ontology.
RELATION_SCHEMA: dict[RelationType, list[tuple[EntityType, EntityType]]] = {
    RelationType.REPORTED: [(EntityType.CUSTOMER, EntityType.SUPPORT_TICKET)],
    RelationType.RELATED_TO: [(EntityType.SUPPORT_TICKET, EntityType.INCIDENT)],
    RelationType.AFFECTED: [(EntityType.INCIDENT, EntityType.SERVICE)],
    RelationType.OWNED_BY: [(EntityType.SERVICE, EntityType.TEAM)],
    RelationType.CAUSED_BY: [(EntityType.INCIDENT, EntityType.ROOT_CAUSE)],
    RelationType.HAS_UPDATE: [(EntityType.INCIDENT, EntityType.INCIDENT_UPDATE)],
    RelationType.HAS_CHUNK: [(EntityType.DOCUMENT, EntityType.CHUNK)],
    RelationType.APPLIES_TO: [(EntityType.SLA_CONTRACT, EntityType.CUSTOMER)],
    RelationType.PART_OF: [(EntityType.SLA_CLAUSE, EntityType.SLA_CONTRACT)],
    RelationType.CONSTRAINS: [(EntityType.SLA_CLAUSE, EntityType.SERVICE)],
    RelationType.MAY_VIOLATE: [(EntityType.INCIDENT, EntityType.SLA_CLAUSE)],
    RelationType.MITIGATES: [(EntityType.RUNBOOK, EntityType.ERROR_SIGNATURE)],
    RelationType.ANALYZES: [(EntityType.POSTMORTEM, EntityType.INCIDENT)],
    RelationType.EXHIBITS: [
        (EntityType.INCIDENT, EntityType.ERROR_SIGNATURE),
        (EntityType.SUPPORT_TICKET, EntityType.ERROR_SIGNATURE),
    ],
}


class JobState(str, Enum):
    QUEUED = "queued"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EXTRACTING = "extracting"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ExtractionMethod(str, Enum):
    STRUCTURED = "structured"    # from typed/normalized source records
    RULE = "rule"                # regex / keyword rules over text
    LLM = "llm"                  # LLM-assisted extraction
    MANUAL = "manual"            # human correction


class AnswerConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class AuditAction(str, Enum):
    MERGE_ENTITY = "merge_entity"
    DELETE_RELATION = "delete_relation"
    EDIT_ENTITY = "edit_entity"
    ADD_RELATION = "add_relation"


SUPPORTED_UPLOAD_TYPES = {".csv", ".json", ".md", ".markdown", ".txt"}
