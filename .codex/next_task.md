# Next Task

## Next executable unit: optional generated-artifact ownership retention

Reproduce the opt-in RAG lifecycle in a temporary workspace: generate it,
disable the profile, then enable it again with a changed configuration. Confirm
that previously generated RAG files retain manifest ownership and are safely
replaceable rather than becoming conflicts.

Preserve scaffolded and user-owned files. Do not add a cleanup command or change
consumer files until the smallest responsible AutoForge manifest lifecycle
behavior is proven.
