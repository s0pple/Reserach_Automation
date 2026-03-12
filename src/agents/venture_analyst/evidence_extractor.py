import asyncio
import uuid
import logging
from typing import List, Dict, Any
from src.core.agent import BaseAgent
from src.schema.venture_state import VentureState, EvidenceClaim, SignalStrength
from src.core.llm import OpenAIClient

logger = logging.getLogger(__name__)

class EvidenceExtractor(BaseAgent):
    """
    The Gatekeeper. Converts raw research text into structured EvidenceClaims.
    Strictly filters out generic noise.
    """
    def __init__(self, name: str = "EvidenceExtractor"):
        super().__init__(name)
        self.llm = OpenAIClient()

    async def process(self, state: VentureState, raw_data_batch: List[Dict[str, str]]) -> VentureState:
        print(f"[{self.name}] Processing {len(raw_data_batch)} raw data entries...")
        state.total_processed_texts += len(raw_data_batch)
        
        for entry in raw_data_batch:
            text = entry.get("text", "")
            url = entry.get("url", "unknown")
            extracted_claims = await self._extract_claims_from_text(text, url, state.domain)
            
            if not extracted_claims:
                state.discarded_claims_count += 1
            
            for claim in extracted_claims:
                if self._is_valid_claim(claim):
                    state.claims[claim.id] = claim
                    print(f"  [CLAIM FOUND] {claim.actor}: {claim.problem[:50]}...")
                else:
                    state.discarded_claims_count += 1
        
        return state

    async def _extract_claims_from_text(self, text: str, url: str, domain: str) -> List[EvidenceClaim]:
        system_prompt = f"""
        You are a Venture Data Miner specializing in '{domain}'. 
        Your task is to extract SPECIFIC pain points from text that are RELEVANT to '{domain}'.
        
        CRITICAL RULE: If the text is about weather, general news, or anything NOT related to '{domain}', return an empty list.
        
        Respond ONLY with a JSON object containing a list 'claims'.
        BLUEPRINT:
        {{
          "claims": [
            {{
              "problem": "exact pain point",
              "actor": "specific job role",
              "context": "when does it happen",
              "frequency": "low|medium|high|critical",
              "willingness_to_pay": "low|medium|high",
              "quote": "original sentence",
              "extraction_reason": "why this is a valid signal for {domain}"
            }}
          ]
        }}
        """
        user_prompt = f"Extract claims from this text from {url}:\n\n{text[:6000]}"
        
        try:
            response = await self.llm.generate_json(system_prompt, user_prompt)
            raw_claims = response.get("claims", [])
            claims = []
            for item in raw_claims:
                claims.append(EvidenceClaim(
                    id=str(uuid.uuid4()),
                    problem=item.get("problem"),
                    actor=item.get("actor"),
                    context=item.get("context"),
                    frequency_signal=SignalStrength(item.get("frequency", "medium")),
                    willingness_to_pay_signal=SignalStrength(item.get("willingness_to_pay", "low")),
                    source_url=url,
                    quote=item.get("quote"),
                    extraction_reason=item.get("extraction_reason"),
                    confidence=0.9
                ))
            return claims
        except Exception as e:
            logger.error(f"Error extracting claims: {e}")
            return []

    def _is_valid_claim(self, claim: EvidenceClaim) -> bool:
        if not claim.problem or len(claim.problem) < 10: return False
        if not claim.actor or claim.actor.lower() in ["anyone", "everyone", "people"]: return False
        return True
