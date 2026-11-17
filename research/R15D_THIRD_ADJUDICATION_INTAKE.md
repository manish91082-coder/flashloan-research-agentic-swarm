# R15D Third-Adjudication Intake Protocol

**Status:** contract and validator only; no genuine third-adjudicator submission has been received.

## Activation condition

Third adjudication is required only for a case where the two validated primary reviewers selected different labels. Do not solicit a third review for unanimous cases. The required case set is derived from the staged primary-review packet, not manually selected by the submitter.

## Blindness and independence boundary

- The third adjudicator must be a real, independently verified reviewer whose stable ID differs from both primary reviewers.
- Unlike the two primary reviewers, the third adjudicator must see both primary review records for each disputed case, including their labels, rationales and evidence references. That is necessary to adjudicate the disagreement.
- The third adjudicator must not see model outputs, model predictions or model-generated rationales.
- The custodian must verify the third adjudicator's identity out of band through a private channel. The validator cannot prove identity or independence.
- Do not publish the third-adjudicator bundle or identity in public repository issues, pull requests, commits or workflow logs.

## Bundle contract

The third-adjudicator bundle contains exactly the disagreement case IDs from the staged packet, each once, and no unanimous cases. Every case must carry the exact canonical source pin, one allowed label, a non-empty rationale, unique evidence references matching the pinned path/range/excerpt SHA-256, confidence in [0,1], a timezone-aware UTC timestamp and a case-level independence attestation.

Bundle-level attestations must confirm independent review, no model-output exposure, access to both primary reviews, conflict disclosure and a conflict statement.

## Validation

Run:

```sh
python scripts/validate_r15d_third_adjudication_submission.py \
  --staged-packet <private-staged-packet.json> \
  --submission <private-third-adjudicator.json>
```

The validator fails closed if the staged packet is not a canonical six-case staged merge, reviewer identities drift across cases, primary reviewer identities collide, any third review is supplied for a unanimous case, any disagreement is omitted, a third identity collides with a primary reviewer, evidence pins mismatch, or any blinding/safety invariant is violated.

A passing validation result confirms structural and source-pin consistency only. It is not an identity certificate, a consensus freeze, or authorization for model inference.

## Final assembly boundary

After every disagreement has a valid third adjudication, the final assembly step must:
1. copy the staged packet into a new output without modifying either source;
2. insert third-adjudicator records only for disagreement cases;
3. derive unanimous consensus only where both primary labels match;
4. use the third adjudicator's label and rationale for disputed cases;
5. run the full adjudication validator with `--require-complete`;
6. keep the freeze state false and model inference unauthorized.

Only the separate freeze writer and independent frozen-manifest verifier may create and attest a frozen ground-truth artifact.
