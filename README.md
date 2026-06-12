# Playground

A personal playground for learning and experimenting with new languages,
tools, and ideas. Nothing here is production code — it's a place to try
things, break things, and learn.

The repository is organized by language, one root directory each:

| Directory   | Language | Status                                              |
| ----------- | -------- | --------------------------------------------------- |
| `python/`   | Python   | Polish NLP comparison (spaCy / Stanza / Trankit)    |
| `scala/`    | Scala    | Learning notes and conventions (scaffold pending)   |
| `react/`    | React    | Empty — to be filled with experiments               |
| `rust/`     | Rust     | Empty — to be filled with experiments               |

## Layout

Each top-level directory is self-contained: it owns its own build setup,
dependencies, and README. Start in the directory for the language you're
working on.

```text
.
├── python/   # Python projects and experiments
├── scala/    # Scala projects and experiments
├── react/    # React / frontend experiments
└── rust/     # Rust projects and experiments
```

## Conventions

- Keep each experiment in its own subdirectory under the language folder.
- Add a short README to anything non-trivial explaining what it is and how
  to run it.
- Prefer simple, readable code over clever code — this is for learning.
