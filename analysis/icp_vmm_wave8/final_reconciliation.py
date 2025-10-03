#!/usr/bin/env python3
"""
Wave 8 - Final Reconciliation & Decision Table
Combine all Wave 8 results and create final decision table
"""

import os
import pandas as pd
import json
import numpy as np
from datetime import datetime

def create_final_decision_table():
    """Create final decision table combining all Wave 8 results"""
    print("Wave 8 - Final Reconciliation & Decision Table")
    print("=" * 50)
    
    # Load Wave 7 final edges
    graph_path = "analysis/icp_vmm_wave7/graph/graph_v1.json"
    with open(graph_path, 'r') as f:
        wave7_results = json.load(f)
    
    wave7_edges = wave7_results['edges']
    print(f"📊 Wave 7 edges: {len(wave7_edges)}")
    
    # Load Wave 8 robustness results
    robustness_path = "analysis/icp_vmm_wave8/robustness/edges_robustness_v1.json"
    with open(robustness_path, 'r') as f:
        robustness_results = json.load(f)
    
    print(f"📊 Wave 8 robustness results: {len(robustness_results)}")
    
    # Create decision table
    decision_table = []
    
    for i, edge in enumerate(wave7_edges):
        source = edge['source']
        target = edge['target']
        lag = edge['lag']
        original_coef = edge['coefficient']
        
        # Find corresponding robustness result
        robustness_result = None
        for robust in robustness_results:
            if (robust['source'] == source and 
                robust['target'] == target and 
                robust['lag'] == lag):
                robustness_result = robust
                break
        
        if robustness_result is None:
            print(f"❌ No robustness result found for {source} -> {target} (lag {lag}s)")
            continue
        
        # Determine final decision
        pass_rate = robustness_result['pass_rate']
        
        if pass_rate >= 0.8:
            decision = 'CONFIRMED'
            reason = f'Robust across scales and subsamples ({pass_rate:.1%} pass rate)'
        elif pass_rate >= 0.5:
            decision = 'FRAGILE'
            reason = f'Partially robust ({pass_rate:.1%} pass rate)'
        else:
            decision = 'REJECTED'
            reason = f'Not robust ({pass_rate:.1%} pass rate)'
        
        # Create decision entry
        decision_entry = {
            'source': source,
            'target': target,
            'lag': lag,
            'original_coefficient': original_coef,
            'pass_rate': pass_rate,
            'decision': decision,
            'reason': reason,
            'scale_tests_passed': sum(1 for test in robustness_result['scale_tests'] if test['pass']),
            'subsample_tests_passed': sum(1 for test in robustness_result['subsample_tests'] if test['pass']),
            'total_tests': len(robustness_result['scale_tests']) + len(robustness_result['subsample_tests'])
        }
        
        decision_table.append(decision_entry)
    
    # Generate summary statistics
    confirmed_edges = [e for e in decision_table if e['decision'] == 'CONFIRMED']
    fragile_edges = [e for e in decision_table if e['decision'] == 'FRAGILE']
    rejected_edges = [e for e in decision_table if e['decision'] == 'REJECTED']
    
    print(f"\n{'='*50}")
    print("FINAL DECISION TABLE SUMMARY")
    print(f"{'='*50}")
    
    print(f"📊 Total edges: {len(decision_table)}")
    print(f"📊 Confirmed: {len(confirmed_edges)}")
    print(f"📊 Fragile: {len(fragile_edges)}")
    print(f"📊 Rejected: {len(rejected_edges)}")
    
    if confirmed_edges:
        print(f"\n✅ Confirmed edges:")
        for edge in confirmed_edges:
            print(f"  {edge['source']} -> {edge['target']} (lag {edge['lag']}s): {edge['pass_rate']:.1%} pass rate")
    
    if fragile_edges:
        print(f"\n⚠️  Fragile edges:")
        for edge in fragile_edges:
            print(f"  {edge['source']} -> {edge['target']} (lag {edge['lag']}s): {edge['pass_rate']:.1%} pass rate")
    
    if rejected_edges:
        print(f"\n❌ Rejected edges:")
        for edge in rejected_edges:
            print(f"  {edge['source']} -> {edge['target']} (lag {edge['lag']}s): {edge['pass_rate']:.1%} pass rate")
    
    # Save decision table
    os.makedirs('analysis/icp_vmm_wave8/summary', exist_ok=True)
    
    with open('analysis/icp_vmm_wave8/summary/decision_table_v1.json', 'w') as f:
        json.dump(decision_table, f, indent=2, default=str)
    
    # Generate markdown report
    md_content = "# Wave 8 Final Decision Table\n\n"
    md_content += f"**Generated**: {datetime.now().isoformat()}\n"
    md_content += f"**Total edges**: {len(decision_table)}\n"
    md_content += f"**Confirmed**: {len(confirmed_edges)}\n"
    md_content += f"**Fragile**: {len(fragile_edges)}\n"
    md_content += f"**Rejected**: {len(rejected_edges)}\n\n"
    
    md_content += "## Summary Statistics\n\n"
    md_content += f"- **Confirmed edges**: {len(confirmed_edges)} ({len(confirmed_edges)/len(decision_table)*100:.1f}%)\n"
    md_content += f"- **Fragile edges**: {len(fragile_edges)} ({len(fragile_edges)/len(decision_table)*100:.1f}%)\n"
    md_content += f"- **Rejected edges**: {len(rejected_edges)} ({len(rejected_edges)/len(decision_table)*100:.1f}%)\n\n"
    
    md_content += "## Decision Table\n\n"
    md_content += "| Source | Target | Lag | Original Coef | Pass Rate | Decision | Reason |\n"
    md_content += "|--------|--------|-----|----------------|-----------|----------|--------|\n"
    
    for edge in decision_table:
        md_content += f"| {edge['source']} | {edge['target']} | {edge['lag']}s | {edge['original_coefficient']:.4f} | {edge['pass_rate']:.1%} | {edge['decision']} | {edge['reason']} |\n"
    
    with open('analysis/icp_vmm_wave8/summary/decision_table_v1.md', 'w') as f:
        f.write(md_content)
    
    # Create final graph with only confirmed edges
    import networkx as nx
    import matplotlib.pyplot as plt
    
    G = nx.DiGraph()
    
    # Add nodes
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    for venue in venues:
        G.add_node(venue)
    
    # Add only confirmed edges
    for edge in confirmed_edges:
        G.add_edge(
            edge['source'], 
            edge['target'], 
            lag=edge['lag'],
            coefficient=edge['original_coefficient'],
            pass_rate=edge['pass_rate']
        )
    
    # Generate graph visualization
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G, k=3, iterations=50)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color='lightgreen', node_size=1000, alpha=0.7)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, edge_color='darkgreen', arrows=True, arrowsize=20, alpha=0.6)
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
    
    # Add edge labels
    edge_labels = {}
    for edge in G.edges():
        coef = G[edge[0]][edge[1]]['coefficient']
        lag = G[edge[0]][edge[1]]['lag']
        pass_rate = G[edge[0]][edge[1]]['pass_rate']
        edge_labels[edge] = f"{coef:.3f}\n({lag}s)\n{pass_rate:.0%}"
    
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
    
    plt.title("Wave 8 Final Causal Graph (Confirmed Edges Only)\n(Pass Rate: 80%+ across scales and subsamples)")
    plt.axis('off')
    plt.tight_layout()
    
    # Ensure directory exists before saving
    os.makedirs('analysis/icp_vmm_wave8/graph', exist_ok=True)
    plt.savefig('analysis/icp_vmm_wave8/graph/graph_wave8_v1.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # Save final graph data
    final_graph_data = {
        'generation_timestamp': datetime.now().isoformat(),
        'total_edges_tested': len(decision_table),
        'confirmed_edges': len(confirmed_edges),
        'fragile_edges': len(fragile_edges),
        'rejected_edges': len(rejected_edges),
        'confirmed_edge_list': confirmed_edges,
        'graph_statistics': {
            'nodes': G.number_of_nodes(),
            'edges': G.number_of_edges(),
            'density': nx.density(G),
            'is_strongly_connected': nx.is_strongly_connected(G),
            'is_weakly_connected': nx.is_weakly_connected(G)
        }
    }
    
    os.makedirs('analysis/icp_vmm_wave8/graph', exist_ok=True)
    with open('analysis/icp_vmm_wave8/graph/graph_wave8_v1.json', 'w') as f:
        json.dump(final_graph_data, f, indent=2, default=str)
    
    print(f"\n📄 Final results saved:")
    print(f"   - analysis/icp_vmm_wave8/summary/decision_table_v1.json")
    print(f"   - analysis/icp_vmm_wave8/summary/decision_table_v1.md")
    print(f"   - analysis/icp_vmm_wave8/graph/graph_wave8_v1.json")
    print(f"   - analysis/icp_vmm_wave8/graph/graph_wave8_v1.png")
    
    return decision_table

if __name__ == "__main__":
    decision_table = create_final_decision_table()
    
    if decision_table is not None:
        print(f"\n✅ Final reconciliation completed - Wave 8 analysis finished")
    else:
        print(f"\n❌ Final reconciliation failed - stopping execution")
