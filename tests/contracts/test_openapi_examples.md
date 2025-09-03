## Contract assertions (to be implemented in pytest)

- `openapi/acd.yml` parses and validates.
- POST `/api/v1/cases/{case_id}/observations` accepts arrays of `Observation`.
- All responses include fields as defined (no extra; no missing).
- Evidence bundle conforms to `schemas/evidence_bundle.schema.json`.
