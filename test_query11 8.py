#!/usr/bin/env python3
"""
Test Query 11 specifically
"""

query = "Identify undercut initiation episodes by market maker; escalate if repeated."
prompt_lower = query.lower()

print(f"Query: {query}")
print(f"Lowercase: {prompt_lower}")
print()

print("Market maker check:")
print(f"  'market maker' in prompt: {'market maker' in prompt_lower}")
print(f"  'undercut' in prompt: {'undercut' in prompt_lower}")
print(f"  'escalate' in prompt: {'escalate' in prompt_lower}")
print(f"  'episodes' in prompt: {'episodes' in prompt_lower}")
print()

print("Fee analysis check:")
print(f"  'vip fee ladder' in prompt: {'vip fee ladder' in prompt_lower}")
print(f"  'inventory shocks' in prompt: {'inventory shocks' in prompt_lower}")
print(f"  'signal' in prompt: {'signal' in prompt_lower}")
print(f"  'explain' in prompt: {'explain' in prompt_lower}")
print(f"  'fee tier' in prompt: {'fee tier' in prompt_lower}")
print(f"  'maker' in prompt: {'maker' in prompt_lower}")
print(f"  'taker' in prompt: {'taker' in prompt_lower}")


