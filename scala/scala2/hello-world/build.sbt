ThisBuild / scalaVersion := "2.13.15"
ThisBuild / version      := "0.1.0-SNAPSHOT"

lazy val root = (project in file("."))
  .settings(
    name := "hello-world"
  )
