#!/usr/bin/env node
/**
 * envsniff npm wrapper
 *
 * Resolution order:
 *   1. If `envsniff` is on PATH → spawn it with all args.
 *   2. Else try `pipx run envsniff` with all args.
 *   3. Else print friendly install instructions and exit 1.
 *
 * All process.argv.slice(2) arguments are forwarded verbatim.
 * The child process exit code is forwarded via process.exit().
 */

"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const args = process.argv.slice(2);

const MARKER = path.join(os.homedir(), ".config", "envsniff", ".welcomed");
const PKG_VERSION = require("../package.json").version;

function markerVersion() {
  try {
    return fs.readFileSync(MARKER, "utf8").trim();
  } catch (_) {
    return "";
  }
}

function writeMarker(ver) {
  try {
    fs.mkdirSync(path.dirname(MARKER), { recursive: true });
    fs.writeFileSync(MARKER, ver, "utf8");
  } catch (_) {
    // read-only fs or permissions issue — silently skip
  }
}

function showWelcomeIfFirstRun() {
  if (markerVersion() === PKG_VERSION) return;

  const logo = [
    "",
    "\x1b[32m\x1b[1m███████╗███╗   ██╗██╗   ██╗███████╗███╗   ██╗██╗███████╗███████╗     █████╗ ██╗",
    "██╔════╝████╗  ██║██║   ██║██╔════╝████╗  ██║██║██╔════╝██╔════╝    ██╔══██╗██║",
    "█████╗  ██╔██╗ ██║██║   ██║███████╗██╔██╗ ██║██║█████╗  █████╗      ███████║██║",
    "██╔══╝  ██║╚██╗██║╚██╗ ██╔╝╚════██║██║╚██╗██║██║██╔══╝  ██╔══╝      ██╔══██║██║",
    "███████╗██║ ╚████║ ╚████╔╝ ███████║██║ ╚████║██║██║     ██║         ██║  ██║██║",
    `╚══════╝╚═╝  ╚═══╝  ╚═══╝  ╚══════╝╚═╝  ╚═══╝╚═╝╚═╝     ╚═╝         ╚═╝  ╚═╝╚═╝\x1b[0m`,
    "",
    `\x1b[1mWelcome to envsniff ${PKG_VERSION}!\x1b[0m Scan your codebase for environment variables and keep \x1b[36m.env.example\x1b[0m in sync.`,
    "",
  ].join("\n");

  process.stderr.write(logo + "\n");
  writeMarker(PKG_VERSION);
}

showWelcomeIfFirstRun();

/**
 * Try to spawn a command. Returns the exit code, or null if the command
 * could not be found (ENOENT).
 */
function trySpawn(cmd, cmdArgs) {
  const result = spawnSync(cmd, cmdArgs, { stdio: "inherit" });
  if (result.error) {
    if (result.error.code === "ENOENT") {
      return null; // command not found
    }
    throw result.error;
  }
  return result.status != null ? result.status : 1;
}

// 1. Try envsniff directly (already on PATH)
const directCode = trySpawn("envsniff", args);
if (directCode !== null) {
  process.exit(directCode);
}

// 2. Fallback: pipx run envsniff
const pipxCode = trySpawn("pipx", ["run", "envsniff", ...args]);
if (pipxCode !== null) {
  process.exit(pipxCode);
}

// 3. Final fallback: print install instructions
console.error(
  [
    "",
    "envsniff could not be found on your PATH.",
    "",
    "Install it with one of the following:",
    "",
    "  pip install envsniff",
    "  pipx install envsniff",
    "",
    "Then re-run: npx envsniff " + args.join(" "),
    "",
  ].join("\n")
);
process.exit(1);
