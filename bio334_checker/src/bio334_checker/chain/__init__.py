"""KairosChain bridge (Phase 5). All KC calls go through this module.

Per ARCHITECTURE.md §7, this module owns the singleton background worker
that polls the SQLite ``submissions`` table for rows missing
``chain_block_ref`` (then ``attestation_id``) and records them on chain
with idempotency keys. Phase 0 ships this as a stub; the worker is
implemented in Phase 5.
"""
