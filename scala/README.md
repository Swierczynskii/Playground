# Scala Developer Guide

This branch is intended as the Scala home for this repository. It does not yet
contain a Scala project scaffold, so this README starts from the beginning: how
the project should be packaged, built, tested, and extended.

## Goals

- Keep the project easy to read for someone learning Scala.
- Prefer simple, explicit code over clever abstractions.
- Use Scala's type system to model intent and invalid states.
- Keep side effects near the edges of the program.
- Make build, test, and run commands predictable.

## Scala philosophy for this repo

Scala combines object-oriented and functional programming. In this repo, use
that combination deliberately:

- Prefer immutable values: use `val` over `var`.
- Prefer small pure functions for core logic.
- Keep I/O, network calls, file access, logging, and process interaction at the
  application boundary.
- Use types to explain the domain instead of passing unstructured strings,
  maps, or tuples through the codebase.
- Use `Option` instead of `null`.
- Use `Either`, `Try`, or a documented effect type for recoverable errors.
- Avoid inheritance-heavy designs unless there is a clear reason.
- Prefer `case class`, `enum`, `trait`, and small modules with focused
  responsibilities.

The default style should be boring, readable Scala.

## Expected project layout

When the Scala scaffold is added, use the standard sbt layout:

```text
.
├── build.sbt
├── project/
│   ├── build.properties
│   └── plugins.sbt
├── src/
│   ├── main/
│   │   ├── scala/
│   │   │   └── playground/
│   │   │       └── Main.scala
│   │   └── resources/
│   └── test/
│       ├── scala/
│       │   └── playground/
│       └── resources/
└── README.md
```

Use `src/main/scala` for production code and `src/test/scala` for tests.
Resources that should be available on the classpath belong in the matching
`resources` directory.

## Packaging conventions

Use one top-level package for this repo:

```scala
package playground
```

Then organize code by feature or domain concept:

```text
playground/
├── Main.scala
├── config/
├── domain/
├── services/
├── adapters/
└── cli/
```

Suggested package responsibilities:

- `playground.domain`: domain models, value objects, enums, and pure rules.
- `playground.services`: application logic that coordinates domain operations.
- `playground.adapters`: code that talks to the outside world.
- `playground.config`: configuration loading and validation.
- `playground.cli`: command-line entry points and argument parsing.

Avoid creating generic packages such as `utils`, `helpers`, or `common` until a
real repeated pattern exists.

## Build tool

Use `sbt` unless there is a specific reason to choose another tool. sbt is the
standard build tool for many Scala projects and supports compilation, tests,
dependency management, formatting plugins, and multi-module builds.

A minimal future `build.sbt` could look like this:

```scala
ThisBuild / scalaVersion := "3.x.x"
ThisBuild / organization := "com.example"

lazy val root = (project in file("."))
  .settings(
    name := "playground-scala",
    version := "0.1.0-SNAPSHOT"
  )
```

Pin exact Scala and plugin versions in the actual project files once the
scaffold is created. Do not rely on globally installed defaults.

## Common developer commands

After the Scala scaffold exists, the expected commands are:

```bash
sbt compile
sbt test
sbt run
sbt console
```

Useful sbt tasks:

- `sbt compile`: compile production code.
- `sbt test`: run tests.
- `sbt run`: run the main application.
- `sbt console`: open a Scala REPL with the project classpath.
- `sbt clean`: remove generated build output.

If formatting and linting are configured later, document the exact commands here
instead of assuming developer-specific setup.

## Testing approach

Tests should explain behavior, not implementation details.

Recommended testing structure:

```text
src/test/scala/playground/
├── domain/
├── services/
└── adapters/
```

Guidelines:

- Put most tests around pure domain and service code.
- Keep adapter tests small and explicit.
- Prefer deterministic tests.
- Avoid tests that require network access unless clearly marked as integration
  tests.
- Test edge cases around parsing, validation, errors, and empty inputs.

## Error handling

Avoid throwing exceptions for expected business failures. Prefer explicit return
types:

```scala
def parsePort(value: String): Either[String, Int]
```

Use exceptions for truly exceptional failures or when interacting with Java APIs
that already throw.

At application boundaries, convert internal errors into user-facing messages,
HTTP responses, exit codes, or logs.

## Dependency guidance

Do not add dependencies casually. Before adding one, ask:

- Is the standard library enough?
- Is the dependency maintained?
- Is it compatible with the chosen Scala version?
- Does it solve a stable problem in the repo?
- Is the added complexity worth it?

Prefer a small dependency set while the project is young.

## Adding new code

When adding a new feature:

1. Start with the domain model.
2. Add pure functions for core rules.
3. Add service code to coordinate behavior.
4. Add adapters for files, network, databases, or external APIs.
5. Add tests close to the behavior being introduced.
6. Update this README if commands, layout, or conventions change.

Keep each change focused. Avoid mixing project setup, refactors, and feature
work in one commit unless they are inseparable.

## Current repository state

At the time this README was added, this branch did not yet contain a Scala
scaffold. The next practical step is to add one of the following:

- a minimal sbt application,
- a minimal sbt library,
- or a Scala CLI experiment if this branch is only for learning snippets.

For a durable repo project, prefer sbt.

