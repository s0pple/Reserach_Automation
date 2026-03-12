from typing import List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

class SignalStrength(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class EvidenceClaim(BaseModel):
    """
    The atomic unit of truth in the venture analysis.
    Extracted from raw research data.
    """
    id: str
    problem: str = Field(..., description="Clear description of the pain point")
    actor: str = Field(..., description="Who specifically has this problem?")
    context: str = Field(..., description="In what situation does this occur?")
    
    # Signals
    frequency_signal: SignalStrength = SignalStrength.MEDIUM
    willingness_to_pay_signal: SignalStrength = SignalStrength.LOW
    
    # Metadata
    source_url: str
    quote: Optional[str] = None
    extracted_at: datetime = Field(default_factory=datetime.now)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    
    # Validation
    is_negative_evidence: bool = False # If True, this supports why a solution might NOT work
    extraction_reason: Optional[str] = Field(None, description="Why was this claim extracted?")

class UnsolvedConstraint(BaseModel):
    """
    Why has this not been solved yet?
    """
    category: str # e.g., "Technical", "Regulatory", "Behavioral", "Economic"
    description: str
    evidence_ids: List[str] = [] # References to EvidenceClaims

class MarketTimingSignal(BaseModel):
    """
    A specific tailwind or enabler that makes 'now' the right time.
    """
    category: str # 'Tech Shift', 'Regulation', 'Cost Collapse', 'Behavior Shift'
    description: str
    source_evidence: Optional[str] = None
    impact_level: str # 'low', 'medium', 'high', 'transformative'

class StrategyRisk(BaseModel):
    """
    A specific risk factor identified by the Skeptic.
    """
    vector: str # 'Incumbent Reaction', 'Distribution Risk', 'Switching Costs'
    critique: str
    severity: str # 'low', 'medium', 'high', 'fatal'

class StrategicOption(BaseModel):
    """
    A specific winning strategy for an OpportunityNode.
    """
    title: str
    description: str
    strategy_type: str # e.g. 'Verticalization', 'API-first', 'Cost Disruption'
    rationale: str # Why this works given history/gaps
    implementation_difficulty: str # 'low', 'medium', 'high'
    potential_moat: str # How it protects against competitors
    
    # Skeptic Critique (Phase 6)
    risks: List[StrategyRisk] = []
    kill_score: float = 0.0 # 0-10, where 10 means 'Absolute Kill'
    skeptic_verdict: Optional[str] = None # e.g. 'Viable but Risky', 'Dead on Arrival'

class OpportunityNode(BaseModel):
    """
    A refined product concept synthesized from multiple EvidenceClaims.
    The 'Gold Bar' created from raw gold pieces.
    """
    id: str
    title: str
    description: str
    actor: str = Field(..., description="The primary user/buyer of this solution")
    core_task: str = Field(..., description="The specific workflow being automated/improved")
    
    # Relationships
    claims: List[str] = [] # References to EvidenceClaim IDs
    constraints: List[UnsolvedConstraint] = []
    
    # Aggregated Metrics
    claim_count: int = 0
    frequency_score: float = 0.0 # Aggregated from claims
    wtp_score: float = 0.0 # Aggregated Willingness To Pay signals
    source_diversity: int = 0 # Number of unique sources
    
    # Final Scoring
    pain_intensity: float = 0.0
    market_timing_score: float = 0.0
    build_feasibility: float = 0.0
    opportunity_score: float = 0.0
    
    # Competition & Gaps (Phase 2)
    competitors: List[str] = [] # Top 5 players
    weakness_patterns: List[str] = [] # Common complaints (e.g. 'expensive', 'bad UI')
    feature_gaps: List[str] = [] # What's missing in existing tools?
    gap_description: Optional[str] = None # The synthesized "Market Gap"
    
    # Historical Context (Phase 3)
    historical_attempts: List[str] = [] # Names of dead startups/projects
    failure_patterns: List[str] = [] # Why they failed
    structural_constraints: List[str] = [] # Hard blockers
    strategic_insight: Optional[str] = None # Synthesized lesson from history

    # Market Timing (Phase 4)
    timing_signals: List[MarketTimingSignal] = []
    timing_verdict: Optional[str] = None # 'Early', 'Perfect', 'Late'

    # Strategy & Differentiation (Phase 5)
    strategies: List[StrategicOption] = []

    metadata: Dict[str, Any] = {}

class IdeaCluster(BaseModel):
    """
    A group of related OpportunityNodes (a product family).
    """
    id: str
    name: str
    theme: str
    nodes: List[str] = [] # References to OpportunityNode IDs

class VentureState(BaseModel):
    """
    The global state for the Venture Analyst Machine.
    """
    domain: str
    initial_context: Optional[str] = None
    
    # The Knowledge Graph
    claims: Dict[str, EvidenceClaim] = {}
    nodes: Dict[str, OpportunityNode] = {}
    clusters: Dict[str, IdeaCluster] = {}
    
    # Metrics
    total_processed_texts: int = 0
    discarded_claims_count: int = 0
    
    # Research History
    raw_sources: List[str] = []
    current_iteration: int = 1
    max_iterations: int = 5
    
    metadata: Dict[str, Any] = {}
