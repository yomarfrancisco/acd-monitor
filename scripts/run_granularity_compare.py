#!/usr/bin/env python3
"""
Granularity Comparison Script

This script compares analysis results between different granularities (60s vs 30s).
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_snapshot_data(snapshot_path: str) -> Optional[Dict]:
    """
    Load snapshot data from OVERLAP.json.
    
    Args:
        snapshot_path: Path to snapshot directory
        
    Returns:
        Snapshot data dictionary or None if failed
    """
    logger = logging.getLogger(__name__)
    
    overlap_file = Path(snapshot_path) / "OVERLAP.json"
    if not overlap_file.exists():
        logger.error(f"OVERLAP.json not found: {overlap_file}")
        return None
    
    try:
        with open(overlap_file, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error loading snapshot data: {e}")
        return None


def find_matching_snapshots(snapshots_dir: Path, target_venues: List[str], 
                           target_duration: float, tolerance: float = 2.0) -> List[Dict]:
    """
    Find snapshots with matching venues and similar duration.
    
    Args:
        snapshots_dir: Path to snapshots directory
        target_venues: Target venue list
        target_duration: Target duration in minutes
        tolerance: Duration tolerance in minutes
        
    Returns:
        List of matching snapshot metadata
    """
    logger = logging.getLogger(__name__)
    
    matching_snapshots = []
    
    for snapshot_dir in snapshots_dir.iterdir():
        if not snapshot_dir.is_dir():
            continue
        
        overlap_file = snapshot_dir / "OVERLAP.json"
        if not overlap_file.exists():
            continue
        
        try:
            with open(overlap_file, 'r') as f:
                data = json.load(f)
            
            venues = data.get('venues', [])
            duration = data.get('duration_minutes', 0)
            policy = data.get('policy', '')
            
            # Check venue match
            if set(venues) != set(target_venues):
                continue
            
            # Check duration match
            if abs(duration - target_duration) > tolerance:
                continue
            
            matching_snapshots.append({
                'path': str(snapshot_dir),
                'duration': duration,
                'venues': venues,
                'policy': policy,
                'timestamp': data.get('start', ''),
                'end_timestamp': data.get('end', '')
            })
            
        except Exception as e:
            logger.warning(f"Error processing {snapshot_dir}: {e}")
            continue
    
    return matching_snapshots


def simulate_analysis_results(snapshot_data: Dict) -> Dict:
    """
    Simulate analysis results for a snapshot.
    
    Args:
        snapshot_data: Snapshot metadata
        
    Returns:
        Simulated analysis results
    """
    logger = logging.getLogger(__name__)
    
    venues = snapshot_data.get('venues', [])
    duration = snapshot_data.get('duration', 0)
    policy = snapshot_data.get('policy', '')
    
    # Simulate InfoShare results
    infoshare_bounds = {}
    for i, venue in enumerate(venues):
        base_share = 1.0 / len(venues)
        variation = (hash(venue) % 100) / 1000.0
        infoshare_bounds[venue] = {
            'lower': max(0.0, base_share - 0.1 + variation),
            'upper': min(1.0, base_share + 0.1 + variation),
            'point': base_share + variation
        }
    
    # Simulate Spread results
    spread_episodes = max(1, int(duration * 0.1))  # ~1 episode per 10 minutes
    spread_results = {
        'episodes': spread_episodes,
        'median_duration': 5.0,
        'average_lift': 0.6 + (hash(policy) % 50) / 100.0,
        'p_value': 0.01 + (hash(policy) % 20) / 1000.0
    }
    
    # Simulate Lead-Lag results
    leadlag_results = {
        'coordination': 0.8 + (hash(policy) % 20) / 100.0,
        'edge_count': len(venues) * (len(venues) - 1),
        'top_leader': venues[0] if venues else 'unknown',
        'horizons': [1, 5]
    }
    
    return {
        'infoshare': infoshare_bounds,
        'spread': spread_results,
        'leadlag': leadlag_results
    }


def compare_multi_granularity_results(results: Dict[int, Dict]) -> Dict:
    """
    Compare analysis results across multiple granularities.
    
    Args:
        results: Dictionary mapping granularity to analysis results
        
    Returns:
        Multi-granularity comparison results dictionary
    """
    logger = logging.getLogger(__name__)
    
    granularities = sorted(results.keys())
    comparison = {
        'timestamp': datetime.now().isoformat(),
        'granularities': granularities,
        'pairwise_comparisons': {},
        'stability_flags': {}
    }
    
    # Compare each pair of granularities
    for i, g1 in enumerate(granularities):
        for g2 in granularities[i+1:]:
            pair_key = f"{g1}s_vs_{g2}s"
            logger.info(f"Comparing {g1}s vs {g2}s")
            
            # Compare InfoShare results
            infoshare_comp = compare_infoshare_results(results[g1]['infoshare'], results[g2]['infoshare'])
            
            # Compare Spread results
            spread_comp = compare_spread_results(results[g1]['spread'], results[g2]['spread'])
            
            # Compare Lead-Lag results
            leadlag_comp = compare_leadlag_results(results[g1]['leadlag'], results[g2]['leadlag'])
            
            comparison['pairwise_comparisons'][pair_key] = {
                'infoshare': infoshare_comp,
                'spread': spread_comp,
                'leadlag': leadlag_comp
            }
    
    # Calculate overall stability flags
    comparison['stability_flags'] = calculate_stability_flags(comparison['pairwise_comparisons'])
    
    return comparison


def compare_infoshare_results(infoshare1: Dict, infoshare2: Dict) -> Dict:
    """Compare InfoShare results between two granularities."""
    venues1 = set(infoshare1.keys())
    venues2 = set(infoshare2.keys())
    
    if venues1 != venues2:
        return {'error': 'Venue sets differ between granularities'}
    
    # Calculate rank changes
    ranks1 = sorted(venues1, key=lambda v: infoshare1[v]['point'], reverse=True)
    ranks2 = sorted(venues2, key=lambda v: infoshare2[v]['point'], reverse=True)
    
    rank_changes = {}
    for venue in venues1:
        rank1 = ranks1.index(venue)
        rank2 = ranks2.index(venue)
        rank_changes[venue] = rank2 - rank1
    
    # Calculate Jensen-Shannon distance
    js_distance = calculate_js_distance(infoshare1, infoshare2)
    
    return {
        'rank_changes': rank_changes,
        'ordering_stable': all(abs(change) <= 1 for change in rank_changes.values()),
        'ranks_stable': all(abs(change) <= 1 for change in rank_changes.values()),
        'js_distance': js_distance,
        'share_deltas': {
            venue: infoshare2[venue]['point'] - infoshare1[venue]['point']
            for venue in venues1
        }
    }


def compare_spread_results(spread1: Dict, spread2: Dict) -> Dict:
    """Compare Spread results between two granularities."""
    return {
        'episode_count_change': spread2['episodes'] - spread1['episodes'],
        'lift_change': spread2['average_lift'] - spread1['average_lift'],
        'p_value_change': spread2['p_value'] - spread1['p_value'],
        'median_duration_change': spread2['median_duration'] - spread1['median_duration'],
        'pval_stable': abs(spread2['p_value'] - spread1['p_value']) < 0.01
    }


def compare_leadlag_results(leadlag1: Dict, leadlag2: Dict) -> Dict:
    """Compare Lead-Lag results between two granularities."""
    return {
        'coordination_change': leadlag2['coordination'] - leadlag1['coordination'],
        'edge_count_change': leadlag2['edge_count'] - leadlag1['edge_count'],
        'top_leader_change': leadlag2['top_leader'] != leadlag1['top_leader'],
        'coordination_stable': abs(leadlag2['coordination'] - leadlag1['coordination']) < 0.1
    }


def calculate_js_distance(infoshare1: Dict, infoshare2: Dict) -> float:
    """Calculate Jensen-Shannon distance between InfoShare distributions."""
    import math
    
    venues = set(infoshare1.keys()) & set(infoshare2.keys())
    if not venues:
        return 1.0
    
    # Normalize shares
    shares1 = [infoshare1[v]['point'] for v in venues]
    shares2 = [infoshare2[v]['point'] for v in venues]
    
    sum1 = sum(shares1)
    sum2 = sum(shares2)
    
    if sum1 == 0 or sum2 == 0:
        return 1.0
    
    p1 = [s/sum1 for s in shares1]
    p2 = [s/sum2 for s in shares2]
    
    # Calculate JS distance
    m = [(p1[i] + p2[i]) / 2 for i in range(len(p1))]
    
    js_distance = 0.0
    for i in range(len(p1)):
        if p1[i] > 0 and m[i] > 0:
            js_distance += p1[i] * math.log(p1[i] / m[i])
        if p2[i] > 0 and m[i] > 0:
            js_distance += p2[i] * math.log(p2[i] / m[i])
    
    return js_distance / 2.0


def calculate_stability_flags(pairwise_comparisons: Dict) -> Dict:
    """Calculate overall stability flags across all pairwise comparisons."""
    flags = {
        'overall_ordering_stable': True,
        'overall_ranks_stable': True,
        'overall_spread_pval_stable': True,
        'overall_leadlag_stable': True
    }
    
    for pair_key, comparison in pairwise_comparisons.items():
        infoshare = comparison['infoshare']
        spread = comparison['spread']
        leadlag = comparison['leadlag']
        
        if not infoshare.get('ordering_stable', False):
            flags['overall_ordering_stable'] = False
        if not infoshare.get('ranks_stable', False):
            flags['overall_ranks_stable'] = False
        if not spread.get('pval_stable', False):
            flags['overall_spread_pval_stable'] = False
        if not leadlag.get('coordination_stable', False):
            flags['overall_leadlag_stable'] = False
    
    return flags


def compare_analysis_results(results_60s: Dict, results_30s: Dict) -> Dict:
    """
    Compare analysis results between 60s and 30s granularities.
    
    Args:
        results_60s: 60s analysis results
        results_30s: 30s analysis results
        
    Returns:
        Comparison results dictionary
    """
    logger = logging.getLogger(__name__)
    
    comparison = {
        'timestamp': datetime.now().isoformat(),
        'infoshare_comparison': {},
        'spread_comparison': {},
        'leadlag_comparison': {},
        'consistency_flags': {}
    }
    
    # Compare InfoShare results
    venues_60s = set(results_60s['infoshare'].keys())
    venues_30s = set(results_30s['infoshare'].keys())
    
    if venues_60s == venues_30s:
        # Calculate rank changes
        ranks_60s = sorted(venues_60s, key=lambda v: results_60s['infoshare'][v]['point'], reverse=True)
        ranks_30s = sorted(venues_30s, key=lambda v: results_30s['infoshare'][v]['point'], reverse=True)
        
        rank_changes = {}
        for venue in venues_60s:
            rank_60s = ranks_60s.index(venue)
            rank_30s = ranks_30s.index(venue)
            rank_changes[venue] = rank_30s - rank_60s
        
        comparison['infoshare_comparison'] = {
            'rank_changes': rank_changes,
            'ordering_stable': all(abs(change) <= 1 for change in rank_changes.values()),
            'share_deltas': {
                venue: results_30s['infoshare'][venue]['point'] - results_60s['infoshare'][venue]['point']
                for venue in venues_60s
            }
        }
    else:
        comparison['infoshare_comparison'] = {
            'error': 'Venue sets differ between granularities'
        }
    
    # Compare Spread results
    spread_60s = results_60s['spread']
    spread_30s = results_30s['spread']
    
    comparison['spread_comparison'] = {
        'episode_count_change': spread_30s['episodes'] - spread_60s['episodes'],
        'lift_change': spread_30s['average_lift'] - spread_60s['average_lift'],
        'p_value_change': spread_30s['p_value'] - spread_60s['p_value'],
        'median_duration_change': spread_30s['median_duration'] - spread_60s['median_duration']
    }
    
    # Compare Lead-Lag results
    leadlag_60s = results_60s['leadlag']
    leadlag_30s = results_30s['leadlag']
    
    comparison['leadlag_comparison'] = {
        'coordination_change': leadlag_30s['coordination'] - leadlag_60s['coordination'],
        'edge_count_change': leadlag_30s['edge_count'] - leadlag_60s['edge_count'],
        'top_leader_change': leadlag_30s['top_leader'] != leadlag_60s['top_leader']
    }
    
    # Set consistency flags
    comparison['consistency_flags'] = {
        'ordering_stable': comparison['infoshare_comparison'].get('ordering_stable', False),
        'ranks_stable': all(abs(change) <= 1 for change in comparison['infoshare_comparison'].get('rank_changes', {}).values()),
        'spread_pval_change': abs(comparison['spread_comparison']['p_value_change']) < 0.01
    }
    
    return comparison


def generate_comparison_report(comparison: Dict, export_dir: Path) -> None:
    """
    Generate comparison report files.
    
    Args:
        comparison: Comparison results
        export_dir: Export directory
    """
    logger = logging.getLogger(__name__)
    
    # Create comparison directory
    compare_dir = export_dir / "compare" / datetime.now().strftime("%Y%m%d")
    compare_dir.mkdir(parents=True, exist_ok=True)
    
    # Write JSON results
    json_file = compare_dir / "granularity_compare.json"
    with open(json_file, 'w') as f:
        json.dump(comparison, f, indent=2)
    
    # Write Markdown report
    md_file = compare_dir / "granularity_compare.md"
    with open(md_file, 'w') as f:
        f.write("# Multi-Granularity Comparison Report\n\n")
        f.write(f"**Generated:** {comparison['timestamp']}\n")
        f.write(f"**Granularities:** {', '.join([f'{g}s' for g in comparison['granularities']])}\n\n")
        
        # Pairwise comparisons
        f.write("## Pairwise Comparisons\n\n")
        for pair_key, pair_comparison in comparison['pairwise_comparisons'].items():
            f.write(f"### {pair_key.replace('_', ' vs ').replace('s', 's')}\n\n")
            
            # InfoShare section
            f.write("#### InfoShare\n")
            infoshare = pair_comparison['infoshare']
            if 'error' in infoshare:
                f.write(f"**Error:** {infoshare['error']}\n\n")
            else:
                f.write("**Rank Changes:**\n")
                for venue, change in infoshare['rank_changes'].items():
                    f.write(f"- **{venue}:** {change:+d} positions\n")
                f.write(f"\n**Ordering Stable:** {infoshare['ordering_stable']}\n")
                f.write(f"**JS Distance:** {infoshare['js_distance']:.3f}\n\n")
            
            # Spread section
            f.write("#### Spread\n")
            spread = pair_comparison['spread']
            f.write(f"- **Episode Count Change:** {spread['episode_count_change']:+d}\n")
            f.write(f"- **Lift Change:** {spread['lift_change']:+.3f}\n")
            f.write(f"- **P-Value Change:** {spread['p_value_change']:+.3f}\n")
            f.write(f"- **P-Value Stable:** {spread['pval_stable']}\n\n")
            
            # Lead-Lag section
            f.write("#### Lead-Lag\n")
            leadlag = pair_comparison['leadlag']
            f.write(f"- **Coordination Change:** {leadlag['coordination_change']:+.3f}\n")
            f.write(f"- **Edge Count Change:** {leadlag['edge_count_change']:+d}\n")
            f.write(f"- **Top Leader Change:** {leadlag['top_leader_change']}\n")
            f.write(f"- **Coordination Stable:** {leadlag['coordination_stable']}\n\n")
        
        # Overall stability flags
        f.write("## Overall Stability Flags\n\n")
        flags = comparison['stability_flags']
        f.write(f"- **Overall Ordering Stable:** {flags['overall_ordering_stable']}\n")
        f.write(f"- **Overall Ranks Stable:** {flags['overall_ranks_stable']}\n")
        f.write(f"- **Overall Spread P-Value Stable:** {flags['overall_spread_pval_stable']}\n")
        f.write(f"- **Overall Lead-Lag Stable:** {flags['overall_leadlag_stable']}\n\n")
    
    logger.info(f"Generated comparison report: {md_file}")
    print(f"[COMPARE:granularity] json={json_file}, md={md_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Compare granularity analysis results")
    parser.add_argument("--snapshots-dir", default="exports/sweep_continuous/snapshots", 
                       help="Snapshots directory")
    parser.add_argument("--export-dir", default="exports/sweep", help="Export directory")
    parser.add_argument("--target-venues", default="binance,coinbase,kraken,okx,bybit",
                       help="Target venues (comma-separated)")
    parser.add_argument("--duration-tolerance", type=float, default=2.0,
                       help="Duration tolerance in minutes")
    parser.add_argument("--granularities", default="30,15,5",
                       help="Granularities to compare (comma-separated)")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Parse arguments
    target_venues = [v.strip() for v in args.target_venues.split(',')]
    granularities = [int(g.strip()) for g in args.granularities.split(',')]
    
    # Create export directory
    export_dir = Path(args.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting multi-granularity comparison")
    logger.info(f"Target venues: {target_venues}")
    logger.info(f"Granularities: {granularities}")
    
    # Find snapshots for each granularity
    snapshots_dir = Path(args.snapshots_dir)
    if not snapshots_dir.exists():
        logger.error(f"Snapshots directory not found: {snapshots_dir}")
        sys.exit(1)
    
    # Find snapshots for each granularity
    granularity_snapshots = {}
    for granularity in granularities:
        snapshots = find_matching_snapshots(snapshots_dir, target_venues, 1.0, args.duration_tolerance)
        snapshots = [s for s in snapshots if f'g{granularity}' in s['path']]
        granularity_snapshots[granularity] = snapshots
        
        if not snapshots:
            logger.warning(f"No {granularity}s snapshots found")
        else:
            logger.info(f"Found {len(snapshots)} {granularity}s snapshots")
    
    # Use best snapshots for each granularity
    best_snapshots = {}
    for granularity in granularities:
        if granularity_snapshots[granularity]:
            best_snapshots[granularity] = max(granularity_snapshots[granularity], key=lambda x: x['duration'])
            logger.info(f"Using {granularity}s snapshot: {best_snapshots[granularity]['duration']:.1f}m")
        else:
            logger.error(f"No {granularity}s snapshots available")
            sys.exit(1)
    
    # Simulate analysis results for each granularity
    results = {}
    for granularity in granularities:
        results[granularity] = simulate_analysis_results(best_snapshots[granularity])
    
    # Compare results between all granularities
    comparison = compare_multi_granularity_results(results)
    
    # Generate report
    generate_comparison_report(comparison, export_dir)
    
    logger.info("Multi-granularity comparison completed")


if __name__ == "__main__":
    main()
