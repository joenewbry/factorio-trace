# Contributing traces

1. Install Factorio 2.0.
2. `pip install factorio-trace` then `factorio-trace install-mod` (optional but useful).
3. `factorio-trace record --contributor <handle> --upload --yes`
4. Play. Alt-tab whenever you want; capture pauses.

Do not upload sessions that include secrets. The recorder already drops input
when Factorio is not frontmost. Skip multiplayer password dialogs.

Code changes: MIT. Uploaded traces: CC BY 4.0 (see LICENSE-DATA).
