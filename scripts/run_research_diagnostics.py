#!/usr/bin/env python3
"""
Research Mode Diagnostics Script

Runs comprehensive diagnostics on research bundles including:
- InfoShare analysis (leader persistence, dominance patterns)
- Spread Convergence (clustering, episode analysis)
- Lead-Lag (coordination, edge analysis)
- Cross-test coherence (consistency across analyses)

Outputs RESEARCH_DECISION.md with [RESEARCH:FLAGGED] or [RESEARCH:CLEAR] decisions.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_evidence_md(evidence_file: Path) -> Dict[str, Any]:
    """Load and parse EVIDENCE.md file."""
    if not evidence_file.exists():
        raise FileNotFoundError(f"EVIDENCE.md not found: {evidence_file}")
    
    content = evidence_file.read_text()
    sections = {}
    
    # Parse BEGIN/END blocks
    import re
    pattern = r'## (\w+)\s*\nBEGIN\s*\n(.*?)\nEND'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for section_name, section_content in matches:
        try:
            # Try to parse as JSON
            sections[section_name] = json.loads(section_content.strip())
        except json.JSONDecodeError:
            # Store as text if not JSON
            sections[section_name] = section_content.strip()
    
    return sections

def analyze_infoshare_patterns(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze InfoShare patterns for research diagnostics."""
    patterns = {
        "leader_persistence": False,
        "dominance_threshold": 0.0,
        "venue_concentration": 0.0,
        "flags": []
    }
    
    # Check if InfoShare results exist
    if "INFO SHARE SUMMARY" in evidence:
        infoshare = evidence["INFO SHARE SUMMARY"]
        if isinstance(infoshare, dict):
            # Look for dominance patterns
            if "venues" in infoshare:
                venue_shares = infoshare["venues"]
                if isinstance(venue_shares, dict):
                    max_share = max(venue_shares.values()) if venue_shares else 0
                    patterns["dominance_threshold"] = max_share
                    
                    # Check for dominance (>0.6)
                    if max_share > 0.6:
                        patterns["flags"].append(f"Dominant venue: {max_share:.3f}")
                        patterns["leader_persistence"] = True
                    
                    # Check venue concentration
                    total_shares = sum(venue_shares.values()) if venue_shares else 0
                    if total_shares > 0:
                        patterns["venue_concentration"] = max_share / total_shares
                        if patterns["venue_concentration"] > 0.7:
                            patterns["flags"].append(f"High concentration: {patterns['venue_concentration']:.3f}")
    
    return patterns

def analyze_spread_patterns(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze Spread Convergence patterns for research diagnostics."""
    patterns = {
        "episode_count": 0,
        "clustering_detected": False,
        "compression_ratio": 0.0,
        "flags": []
    }
    
    if "SPREAD SUMMARY" in evidence:
        spread = evidence["SPREAD SUMMARY"]
        if isinstance(spread, dict):
            episodes = spread.get("episodes", 0)
            patterns["episode_count"] = episodes
            
            # Check for clustering (high episode count)
            if episodes > 10:
                patterns["clustering_detected"] = True
                patterns["flags"].append(f"High episode count: {episodes}")
            
            # Check compression ratio if available
            if "compression_ratio" in spread:
                patterns["compression_ratio"] = spread["compression_ratio"]
                if patterns["compression_ratio"] > 0.8:
                    patterns["flags"].append(f"High compression: {patterns['compression_ratio']:.3f}")
    
    return patterns

def analyze_leadlag_patterns(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze Lead-Lag patterns for research diagnostics."""
    patterns = {
        "coordination_score": 0.0,
        "edge_count": 0,
        "top_leader": None,
        "flags": []
    }
    
    if "LEADLAG SUMMARY" in evidence:
        leadlag = evidence["LEADLAG SUMMARY"]
        if isinstance(leadlag, dict):
            coordination = leadlag.get("coordination", 0.0)
            patterns["coordination_score"] = coordination
            
            # Check coordination thresholds
            if coordination > 0.9:
                patterns["flags"].append(f"Very high coordination: {coordination:.3f}")
            elif coordination < 0.3:
                patterns["flags"].append(f"Low coordination: {coordination:.3f}")
            
            # Check for edge information if available
            if "edges" in leadlag:
                edges = leadlag["edges"]
                if isinstance(edges, list):
                    patterns["edge_count"] = len(edges)
                    if patterns["edge_count"] > 20:
                        patterns["flags"].append(f"High edge count: {patterns['edge_count']}")
    
    return patterns

def run_cross_test_coherence(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Run cross-test coherence analysis."""
    coherence = {
        "infoshare_spread_alignment": False,
        "spread_leadlag_alignment": False,
        "overall_coherence": False,
        "flags": []
    }
    
    # Check if all analyses completed successfully
    required_sections = ["INFO SHARE SUMMARY", "SPREAD SUMMARY", "LEADLAG SUMMARY"]
    all_completed = all(section in evidence for section in required_sections)
    
    if not all_completed:
        coherence["flags"].append("Missing analysis sections")
        return coherence
    
    # Check for temporal consistency
    if "OVERLAP" in evidence:
        overlap = evidence["OVERLAP"]
        if isinstance(overlap, dict):
            duration = overlap.get("duration_minutes", 0)
            if duration < 5:
                coherence["flags"].append(f"Short duration: {duration:.1f} minutes")
            elif duration > 30:
                coherence["flags"].append(f"Long duration: {duration:.1f} minutes")
    
    # Check venue consistency
    if "OVERLAP" in evidence:
        overlap = evidence["OVERLAP"]
        if isinstance(overlap, dict):
            venues = overlap.get("venues", [])
            if len(venues) < 3:
                coherence["flags"].append(f"Low venue count: {len(venues)}")
    
    coherence["overall_coherence"] = len(coherence["flags"]) == 0
    return coherence

def generate_research_decision(evidence: Dict[str, Any], granularity: str) -> Dict[str, Any]:
    """Generate research decision based on all diagnostics."""
    decision = {
        "status": "CLEAR",
        "granularity": granularity,
        "timestamp": pd.Timestamp.now().isoformat(),
        "flags": [],
        "metrics": {},
        "reasons": []
    }
    
    # Run all diagnostic analyses
    infoshare_patterns = analyze_infoshare_patterns(evidence)
    spread_patterns = analyze_spread_patterns(evidence)
    leadlag_patterns = analyze_leadlag_patterns(evidence)
    coherence = run_cross_test_coherence(evidence)
    
    # Collect all flags
    all_flags = []
    all_flags.extend(infoshare_patterns["flags"])
    all_flags.extend(spread_patterns["flags"])
    all_flags.extend(leadlag_patterns["flags"])
    all_flags.extend(coherence["flags"])
    
    # Determine decision
    if all_flags:
        decision["status"] = "FLAGGED"
        decision["flags"] = all_flags
        decision["reasons"] = [
            f"InfoShare patterns: {len(infoshare_patterns['flags'])} flags",
            f"Spread patterns: {len(spread_patterns['flags'])} flags", 
            f"Lead-Lag patterns: {len(leadlag_patterns['flags'])} flags",
            f"Coherence issues: {len(coherence['flags'])} flags"
        ]
    else:
        decision["reasons"] = ["No significant patterns detected", "All analyses within normal ranges"]
    
    # Store metrics
    decision["metrics"] = {
        "infoshare": infoshare_patterns,
        "spread": spread_patterns,
        "leadlag": leadlag_patterns,
        "coherence": coherence
    }
    
    return decision

def write_research_decision(decision: Dict[str, Any], output_file: Path):
    """Write RESEARCH_DECISION.md file."""
    content = f"""# Research Diagnostics Decision

## Decision: [RESEARCH:{decision['status']}]

**Granularity**: {decision['granularity']}  
**Timestamp**: {decision['timestamp']}  
**Status**: {decision['status']}

## Flags ({len(decision['flags'])})

{chr(10).join(f"- {flag}" for flag in decision['flags']) if decision['flags'] else "No flags detected"}

## Reasons

{chr(10).join(f"- {reason}" for reason in decision['reasons'])}

## Detailed Metrics

### InfoShare Analysis
- Leader Persistence: {decision['metrics']['infoshare']['leader_persistence']}
- Dominance Threshold: {decision['metrics']['infoshare']['dominance_threshold']:.3f}
- Venue Concentration: {decision['metrics']['infoshare']['venue_concentration']:.3f}

### Spread Analysis  
- Episode Count: {decision['metrics']['spread']['episode_count']}
- Clustering Detected: {decision['metrics']['spread']['clustering_detected']}
- Compression Ratio: {decision['metrics']['spread']['compression_ratio']:.3f}

### Lead-Lag Analysis
- Coordination Score: {decision['metrics']['leadlag']['coordination_score']:.3f}
- Edge Count: {decision['metrics']['leadlag']['edge_count']}
- Top Leader: {decision['metrics']['leadlag']['top_leader'] or 'N/A'}

### Coherence Analysis
- Overall Coherence: {decision['metrics']['coherence']['overall_coherence']}
- InfoShare-Spread Alignment: {decision['metrics']['coherence']['infoshare_spread_alignment']}
- Spread-LeadLag Alignment: {decision['metrics']['coherence']['spread_leadlag_alignment']}

## JSON Decision

```json
{json.dumps(decision, indent=2)}
```
"""
    
    output_file.write_text(content)
    logger.info(f"Research decision written to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Run research diagnostics on evidence bundles")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory path")
    parser.add_argument("--granularity", required=True, help="Granularity (e.g., 30s, 15s)")
    parser.add_argument("--mode", default="research", help="Analysis mode")
    parser.add_argument("--output-file", default="RESEARCH_DECISION.md", help="Output decision file")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    bundle_dir = Path(args.bundle_dir)
    evidence_file = bundle_dir / "EVIDENCE.md"
    output_file = bundle_dir / args.output_file
    
    try:
        # Load evidence
        logger.info(f"Loading evidence from: {evidence_file}")
        evidence = load_evidence_md(evidence_file)
        
        # Generate decision
        logger.info(f"Running diagnostics for {args.granularity} granularity")
        decision = generate_research_decision(evidence, args.granularity)
        
        # Write decision file
        write_research_decision(decision, output_file)
        
        # Print summary
        status = decision['status']
        flag_count = len(decision['flags'])
        print(f"[RESEARCH:{status}] {args.granularity} - {flag_count} flags")
        
        if decision['flags']:
            print("Flags:")
            for flag in decision['flags']:
                print(f"  - {flag}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Diagnostics failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
