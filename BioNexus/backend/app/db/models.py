from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Dialect-agnostic BigInteger with integer fallback for SQLite autoincrement
AutoPK = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    """Declarative Base for all BioNexus relational database models."""

    pass


class Compound(Base):
    """Natural compounds, microbial secondary metabolites, and phytochemicals."""

    __tablename__ = "compounds"

    id: Mapped[int] = mapped_column(AutoPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    canonical_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    pubchem_cid: Mapped[Optional[int]] = mapped_column(AutoPK, nullable=True, index=True)
    smiles: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    molecular_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Compound(id={self.id}, name='{self.name}', canonical_id='{self.canonical_id}')>"


class Protein(Base):
    """Protein entities and receptor targets (e.g. UniProt records)."""

    __tablename__ = "proteins"

    id: Mapped[int] = mapped_column(AutoPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    canonical_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Protein(id={self.id}, name='{self.name}', canonical_id='{self.canonical_id}')>"


class Gene(Base):
    """Gene entities (e.g. NCBI / Ensembl gene records)."""

    __tablename__ = "genes"

    id: Mapped[int] = mapped_column(AutoPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    canonical_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Gene(id={self.id}, name='{self.name}', canonical_id='{self.canonical_id}')>"


class Pathway(Base):
    """Biological signaling and metabolic pathways (e.g. Reactome / KEGG)."""

    __tablename__ = "pathways"

    id: Mapped[int] = mapped_column(AutoPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    canonical_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Pathway(id={self.id}, name='{self.name}', canonical_id='{self.canonical_id}')>"


class BiologicalProcess(Base):
    """Biological processes and cellular functions (e.g. Gene Ontology BP)."""

    __tablename__ = "biological_processes"

    id: Mapped[int] = mapped_column(AutoPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    canonical_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<BiologicalProcess(id={self.id}, name='{self.name}', canonical_id='{self.canonical_id}')>"


class Relationship(Base):
    """Central graph relationship table linking biological entities across domains."""

    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(AutoPK, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(AutoPK, nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_id: Mapped[int] = mapped_column(AutoPK, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # One-to-many relationship with evidence records
    evidence_records: Mapped[List["Evidence"]] = relationship(
        "Evidence",
        back_populates="relationship",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_rel_source", "source_type", "source_id"),
        Index("ix_rel_target", "target_type", "target_id"),
        Index("ix_rel_type", "relationship_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<Relationship(id={self.id}, {self.source_type}:{self.source_id} "
            f"-[{self.relationship_type}]-> {self.target_type}:{self.target_id})>"
        )


class Evidence(Base):
    """Evidence grounding table storing literature, PMIDs, and experimental database citations."""

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(AutoPK, primary_key=True, autoincrement=True)
    relationship_id: Mapped[int] = mapped_column(
        AutoPK,
        ForeignKey("relationships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_database: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_record_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    evidence_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    relationship: Mapped["Relationship"] = relationship("Relationship", back_populates="evidence_records")

    def __repr__(self) -> str:
        return (
            f"<Evidence(id={self.id}, relationship_id={self.relationship_id}, "
            f"source='{self.source_database}', record_id='{self.source_record_id}')>"
        )
