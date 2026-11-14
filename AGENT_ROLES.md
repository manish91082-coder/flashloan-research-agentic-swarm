# Agent Roles

These are ten logical responsibilities, not ten always-on agents.

1. Research Director: scope, queue, priorities and acceptance gates.
2. GitHub Discovery: query design, pagination and candidate normalization.
3. Protocol Specialist: determine the actual funding primitive, callback interface and protocol version.
4. Solidity Security Auditor: authorization, callback caller/initiator, reentrancy, repayment and accounting.
5. Execution Engineer: analyse scanner, route, simulation and transaction architecture. Research only; never broadcast.
6. Test & Verification: reproduce claims with fixtures, tests and CI artifacts.
7. Economics & Quant: flash fee, pool/DEX fees, gas, slippage, liquidity, MEV and net-profit model.
8. Dependency & License: versions, dependency provenance, licenses and supply-chain risks.
9. Evidence Auditor: exact commit, tree, path, blob SHA, line range, excerpt, claim type and limitations.
10. Continuity & Documentation: canonical project state, decision log, changelog and handoff.

Activation rule: invoke only the specialist checks needed by a candidate's stage. Every agent output is an untrusted proposal. Deterministic schema and evidence validation decide whether a claim can be accepted. Security conclusions are not decided by majority vote.
