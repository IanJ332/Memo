# Phase 08B-1 Candidate10 evidence provenance and gaps

## Provenance chain

This report covers frozen attempt
`20261007T165110Z-19d0ccd6b106` and is derived locally without Jetstream, SSH,
provider, embedding, or hosted-model activity.

The local source is the immutable recovered attempt directory under the
Candidate10 remote-forensic review area. The authoritative completion artifact
has SHA-256
`ca636f62ec87bfad5aa3e456a3584ed65f48bdb585d4747afce34bcbe1700f23`.
Its 23 declared artifacts independently match both expected SHA-256 and byte
counts. The accepted 27-member review ZIP has SHA-256
`43e63ce4632735ba30582a649a942f9dd98a31e33b241045c01d906120a4d5d9`.

The initial fail-closed forensic copy recovered and verified 104 ordinary
files, then stopped at a permission-denied Redis dump. A later narrowly scoped
evidence-completion recovery obtained the remaining readable required files and
the zero-byte Dream scheduling response. The local attempt directory now has
115 ordinary files. The protected 89-byte Redis dump was not read, copied, or
bypassed. Thus, the historical count of 104 describes the first recovery pass,
not the final set of locally available attempt files.

## Indexed primary-evidence reconciliation

`provider-raw-response.json` records 80 provider raw responses and 3 adapter
raw captures. `provider-evidence-index.json` repeats the three adapter captures,
records 15 capability references that collapse to 11 unique paths, and records
one S0 scenario path. Deduplication uses the normalized attempt-relative path.

| Measure | Count |
| --- | ---: |
| Provider raw-response entries | 80 |
| Adapter raw-capture entries | 3 |
| Unique capability-evidence paths | 11 |
| Unique scenario-evidence paths | 1 |
| Deduplicated indexed primary paths | 95 |
| Found locally | 95 |
| SHA-256 verified | 95 |
| Recorded byte expectations | 88 |
| Recorded byte expectations verified | 88 |
| Paths with no recorded byte expectation | 7 |
| Missing indexed paths | 0 |
| Hash mismatches | 0 |
| Byte-count mismatches | 0 |

The seven paths without a recorded byte expectation are capability probe
artifacts that do carry expected SHA-256 values. Their exact actual byte counts
and hashes appear in the verification manifest. They are not missing or hash-
unverifiable; only an independent expected byte count was never recorded.

The 27-member review ZIP contains the required completion artifacts and review
summaries, but it does not contain the 80 child raw-response files, the three
adapter-capture files, or seven capability-probe paths. The new raw-evidence
appendix closes that packaging gap with exact copies of all 95 indexed paths
and both index roots.

## Shareability and byte preservation

All 95 indexed primary paths were assessed as safe to share within the review
scope and were archived as exact original bytes. No artifact was normalized,
reformatted, or silently replaced with a derivative.

`provider-config.json` contains explicit `<REDACTED>` placeholders created by
the original evidence generator. The appendix includes those exact original,
already-redacted bytes; it is not labeled byte-identical to an unredacted file
and no unredacted counterpart was accessed. The OpenAPI response contains
security-related schema field names but no observed credential values.

The zero-byte `provider-raw-responses/015-schedule-dream-1.json` is intentionally
present. Its expected and actual SHA-256 are the standard empty-byte digest,
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## Exclusions and unresolved gaps

- `provider-state/redis/dump.rdb` is a protected database dump and was excluded
  without reading or privilege escalation. It is not referenced by either
  primary-evidence index and is not one of the 23 required completion
  artifacts.
- Attempt-scoped database directories remain broader state residue rather than
  a complete, safe-to-share evidence archive. Their contents were not used to
  fill or infer indexed evidence.
- Effective API and deriver configuration files were conservatively excluded
  from the raw appendix because they are configuration artifacts outside the
  indexed primary-evidence scope. Their required-artifact identities remain
  verified separately in the accepted review bundle.
- Runtime `.env` material, credentials, private keys, protected dumps, and
  unredacted sensitive configuration were excluded. No missing artifact was
  fabricated.
- Provider-root inspection was metadata-only; provider log content is not a
  complete archived evidence source.
- The transport root cause remains unknown. The recovered scientific evidence
  proves remote completion but does not explain why the original SSH channel
  failed to return before the controller timeout.

There are no unresolved gaps in the 95-path indexed primary-evidence set and no
missing required completion artifact. The unresolved gaps concern broader
provider state/log completeness and transport causation, neither of which is
silently promoted to scientific evidence.
