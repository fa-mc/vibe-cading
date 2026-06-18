# CLA signature ledger — machine-maintained

This is an **orphan branch** that stores CLA signatures for vibe-cading. It is
written to automatically by the **CLA Assistant** GitHub Action
(`.github/workflows/cla.yml`, `path-to-signatures: signatures/version2/cla.json`).

**Do not merge this branch into `main`, and do not delete it.** It deliberately
shares no history with `main` — it carries only the signature ledger, never
product code. It lives off `main` (rather than on it) so the CLA bot never needs
to push to the protected default branch; `main`'s branch-protection ruleset stays
fully intact.

See [`CONTRIBUTING.md`](https://github.com/fa-mc/vibe-cading/blob/main/CONTRIBUTING.md)
on `main` for how contributors sign the CLA.
