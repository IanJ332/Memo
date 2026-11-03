# Jetstream2 runtime baseline

This is a historical observation, not a current state check. Phase 2B-5A
recorded the final lifecycle SHELVED_OFFLOADED → ACTIVE → SHELVED on November
2–3, 2026 UTC. Consult [the public preservation summary](PHASE2_PUBLICATION.md) for
scientific outcomes and preservation details. This newer observation supersedes
older September mount and state assumptions; recheck dynamic properties before use.

The observed existing `jisheng3` instance in project `CIS261698` on
Jetstream2/Exosphere ran Ubuntu 24.04 x86_64; the remote user was `exouser`.
Persistent `/dev/sdb` was ext4, UUID
`979b8eac-118a-44f1-aba1-56ce136c8cb8`, mounted at
`/media/volume/jisheng3_volume_2`. Never format it. The accepted Linux runtime
reported Python 3.12.3, SQLite 3.45.1 and OpenSSL 3.0.13. The last inference
used Jetstream2 Direct's `qwen-3.8-27b` chat-completions endpoint, with thinking
explicitly disabled under the V3 contract. Coding-agent choice does not change a
scientific model or endpoint.

The registered endpoint was `https://llm.jetstream-cloud.org/qwen-3.8-27b/v1/chat/completions`.
The compatibility source/runtime inventory SHA-256 was
`d4fab248a37537d9a47121199a4f90c0718eb1a421476f7b3704a3193f3dc1dd`;
the smoke inventory was `6e45e1a818518401dcc2458def9dad574cc289f12ddf4dd1d6c2a8ec18aa2a4f`;
the reused Linux runtime observation was
`d5bb560abe3710645efc4611e7dd272129c3429a9464a42b67044a46c1395dbc`.

The deployed package and runtime identities were recorded with the Phase 2B-5A
qualification and private evidence, not inferred from this document. After any
separately authorized unshelving, minimally verify instance state, permitted
management/SSH access, the device mount and UUID, exact accepted source and
runtime identities, reservation/evidence state, and relevant free space. Perform
full hardware rediscovery only after a material image, flavor, storage or runtime
change. The current IP and instance state are unknown.

Preserve private raw evidence, SQLite ledgers and sidecars; never reset consumed
reservations. Conserve service units. Restore the starting lifecycle state when
permitted; do not automatically shelve an instance already active. Do not
modify unrelated Exosphere resources. Machine-specific access context belongs in
ignored `.local/` files, never in the public repository.
