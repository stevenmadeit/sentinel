# Auth Token Expiry Runbook

1. Inspect token issuer metrics and recent certificate rotations.
2. Validate cache settings for active sessions.
3. Reconcile stale refresh tokens and trigger a manual reset if needed.
