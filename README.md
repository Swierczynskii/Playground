# Playground

A personal playground for learning and experimenting with new languages,
tools, and ideas. It's a place to try things, break things, and learn.

The repository is organized by language, one root directory each:

| Directory   | Language | Description                                              |
| ----------- | -------- | --------------------------------------------------- |
| `python/`   | Python   | Python experiments / NLP / webdev / Data Engineering    |
| `scala/`    | Scala    | Scala experiments / Data Engineering / backend development    |
| `react/`    | React    | React / frontend experiments               |
| `rust/`     | Rust     | Rust / backend /  Tauri experiments               |

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
