#!/usr/bin/env python3
"""
ICP-VMM Schema Validator

Validates MANIFEST.json against v1.0.0 schema specification.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any
import jsonschema

def load_schema() -> Dict[str, Any]:
    """Load the v1.0.0 JSON schema."""
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "ACD ICP-VMM Manifest",
        "type": "object",
        "required": ["specVersion", "run", "data", "methods", "env", "results", "integrity", "provenance"],
        "properties": {
            "specVersion": {"type": "string", "pattern": "^1\\.\\d+\\.\\d+$"},
            "run": {
                "type": "object",
                "required": ["windowId", "symbol", "venues", "tsStart", "tsEnd", "runStatus", "generatedAt", "seed"],
                "properties": {
                    "windowId": {"type": "string"},
                    "symbol": {"type": "string"},
                    "venues": {"type": "array", "items": {"type": "string"}, "minItems": 2},
                    "tsStart": {"type": "string", "format": "date-time"},
                    "tsEnd": {"type": "string", "format": "date-time"},
                    "observations": {"type": "object", "additionalProperties": {"type": "integer", "minimum": 0}},
                    "coverage": {"type": "object", "additionalProperties": {"type": "number", "minimum": 0, "maximum": 1}},
                    "schemaStatus": {"type": "string", "enum": ["complete", "incomplete"]},
                    "missingFields": {"type": "array", "items": {"type": "string"}},
                    "runStatus": {"type": "string", "enum": ["PROVISIONAL", "INSUFFICIENT", "INVARIANT", "VARIANT", "ERROR"]},
                    "statusReason": {"type": "string"},
                    "generatedAt": {"type": "string", "format": "date-time"},
                    "seed": {"type": "integer"}
                }
            },
            "data": {
                "type": "object",
                "required": ["s3Input", "s3Output"],
                "properties": {
                    "s3Input": {"type": "array", "items": {"type": "string"}},
                    "s3Output": {"type": "string"},
                    "symbols": {"type": "array", "items": {"type": "string"}}
                }
            },
            "methods": {
                "type": "object",
                "required": ["vmm", "icp", "preprocess"],
                "properties": {
                    "preprocess": {
                        "type": "object",
                        "properties": {
                            "returnHorizonSec": {"type": "integer"},
                            "detrend": {"type": "string", "enum": ["none", "demean", "hp"]},
                            "resample": {"type": "string", "enum": ["raw", "1s", "2s", "5s", "30s"]},
                            "fieldsUsed": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "vmm": {
                        "type": "object",
                        "properties": {
                            "johansenMode": {"type": "string", "enum": ["johansen", "var_fevd_fallback"]},
                            "lags": {"type": "integer"},
                            "rank": {"type": "integer"},
                            "infoShare": {"type": "object", "additionalProperties": {"type": "number"}}
                        }
                    },
                    "icp": {
                        "type": "object",
                        "properties": {
                            "fdrQ": {"type": "number"},
                            "testedParams": {"type": "array", "items": {"type": "string"}},
                            "invariantParams": {"type": "array", "items": {"type": "string"}},
                            "variantParams": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            },
            "env": {
                "type": "object",
                "required": ["bins", "counts", "minBinSize"],
                "properties": {
                    "bins": {
                        "type": "object",
                        "properties": {
                            "session": {"type": "array", "items": {"type": "string"}},
                            "vwapSide": {"type": "array", "items": {"type": "string"}},
                            "highLow": {"type": "array", "items": {"type": "string"}},
                            "liquidity": {"type": "array", "items": {"type": "string"}},
                            "leadership": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "counts": {
                        "type": "object",
                        "additionalProperties": {"type": "object", "additionalProperties": {"type": "integer", "minimum": 0}}
                    },
                    "minBinSize": {"type": "integer"}
                }
            },
            "results": {
                "type": "object",
                "properties": {
                    "leadershipIndex": {"type": "number"},
                    "summary": {"type": "string"}
                }
            },
            "integrity": {
                "type": "object",
                "required": ["inputs", "outputs", "manifestHash"],
                "properties": {
                    "inputs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["path", "sha256", "bytes"],
                            "properties": {
                                "path": {"type": "string"},
                                "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                                "bytes": {"type": "integer", "minimum": 0}
                            }
                        }
                    },
                    "outputs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["path", "sha256", "bytes"],
                            "properties": {
                                "path": {"type": "string"},
                                "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                                "bytes": {"type": "integer", "minimum": 0}
                            }
                        }
                    },
                    "manifestHash": {"type": "string", "pattern": "^[a-f0-9]{64}$"}
                }
            },
            "provenance": {
                "type": "object",
                "required": ["git", "container", "runtime", "ci"],
                "properties": {
                    "git": {
                        "type": "object",
                        "properties": {
                            "repo": {"type": "string"},
                            "sha": {"type": "string"},
                            "branch": {"type": "string"},
                            "dirty": {"type": "boolean"}
                        }
                    },
                    "container": {
                        "type": "object",
                        "properties": {
                            "image": {"type": "string"},
                            "tag": {"type": "string"},
                            "digest": {"type": "string"}
                        }
                    },
                    "runtime": {
                        "type": "object",
                        "properties": {
                            "python": {"type": "string"},
                            "numpy": {"type": "string"},
                            "pandas": {"type": "string"},
                            "statsmodels": {"type": "string"}
                        }
                    },
                    "ci": {
                        "type": "object",
                        "properties": {
                            "provider": {"type": "string"},
                            "runId": {"type": "string"},
                            "jobUrl": {"type": "string"}
                        }
                    }
                }
            }
        }
    }
    return schema

def validate_manifest(manifest_path: str) -> bool:
    """Validate MANIFEST.json against schema."""
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        schema = load_schema()
        jsonschema.validate(manifest, schema)
        
        print(f"✅ MANIFEST.json validation passed: {manifest_path}")
        return True
        
    except jsonschema.ValidationError as e:
        print(f"❌ Schema validation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

def main():
    """Main validation function."""
    if len(sys.argv) != 2:
        print("Usage: python schema_validator.py <manifest_path>")
        sys.exit(1)
    
    manifest_path = sys.argv[1]
    if not Path(manifest_path).exists():
        print(f"❌ Manifest file not found: {manifest_path}")
        sys.exit(1)
    
    if validate_manifest(manifest_path):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
