# Phase 08B-1 Candidate10 primary raw-evidence appendix reference

## Identity and publication status

| Field | Value |
| --- | --- |
| Attempt | `20261007T165110Z-19d0ccd6b106` |
| Local archive filename | `phase08b1-candidate10-primary-raw-evidence-appendix.zip` |
| Archive SHA-256 | `3eae5e4c07552c562aaff56bd5f1de2eb5ca61648d6a99d29ff2ac159d6b91df` |
| Archive bytes | `60291` |
| ZIP members | `99` |
| Repository publication status | **NOT PUBLISHED** |
| Raw evidence published | **NO** |

The archive is preserved locally outside the tracked repository. It is not
included in this publication commit, and this reference must not be read as a
claim that the archive or its raw evidence is publicly available.

## Contents represented by the identity

The immutable ZIP contains one README, the exact reviewed evidence-verification
manifest, exact copies of the two evidence-index roots, and exact original
bytes for all 95 deduplicated indexed primary-evidence paths. Those paths are
80 provider raw responses, three adapter raw captures, 11 unique capability
evidence paths, and one direct S0 scenario-evidence path.

The external tracked verification manifest is
[`phase-08b1-candidate10-evidence-verification.json`](../../manifests/phase-08b1-candidate10-evidence-verification.json).
Its verification records that all 95 indexed files are present and match their
expected SHA-256 values, with all 88 recorded byte expectations also matching.
The remaining seven files have verified hashes and reported actual sizes, but
no independently recorded expected byte count.

## Exclusions and immutability

The archive does not contain the protected Redis database dump, broader
provider-state databases, credentials, private keys, runtime `.env` material,
or non-indexed effective-configuration artifacts. The indexed
`provider-config.json` is preserved as exact original bytes that were already
redacted at source.

Neither the attempt artifacts nor the ZIP were modified for publication. The
full raw evidence remains local and unpublished. Any later publication of the
archive requires separate review and authorization and must preserve this
identity.
