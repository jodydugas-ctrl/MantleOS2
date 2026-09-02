# Hermes Reference Assimilation

Hermes is the first MantleOS 2 reference Default Body. It remains an upstream
dependency and is never vendored into this repository.

## Construction

`mantle assimilate github.com/nousresearch/hermes-agent` performs these bounded
steps:

1. Normalize and clone the GitHub source without submodules.
2. Record the resolved commit, tree, branch, license evidence, and read-only census.
3. Append private-state exclusions to the host `.gitignore`.
4. Add a public `mantle/` delta containing controls, manifest, candidate Primer, and inert adapter source.
5. Create ignored `.mantle/prebirth.json` with birth explicitly unauthorized.
6. Stop without installing dependencies, executing Hermes, activating a plugin, creating a key, or starting a Heartbeat.

The manifest and Git diff are the reproducible delta. The release bundle pins
the upstream baseline and includes checksums so another user can reconstruct the
same candidate Body from the MantleOS release plus Hermes.

## Attachment

The adapter observes documented session, semantic user-turn, model-call,
tool-completion, and session-end hooks. It records tool names, argument names,
status, timing, and a digest—not raw values or results. Ordinary Hermes turns
remain native Hermes behavior. Direct AppAI routing is separately configured in
Hermes `config.yaml` under `mantle.appai_route`; secrets remain in protected
credential storage.

Adapter installation and activation are intentionally not automatic in this
alpha. Construction proves a candidate edge, not adoption authority.

## Verification claims

The pinned gate proves that a clean Hermes clone can receive the delta without
executing foreign code, that the resulting manifest matches the exact upstream
commit, and that Mantle runtime tests pass on Windows and Linux. It does not
claim a born identity, production migration continuity, or permission to alter
Hermes core behavior.

