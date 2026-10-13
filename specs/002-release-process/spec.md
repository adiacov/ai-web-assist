# Feature Specification: Release Process, Update and Downgrade

**Feature Branch**: `002-release-process`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "A release process for awa so users can install, update and downgrade cleanly, and do it from awa itself. SemVer tags (v0.1.0 = current main), GitHub only (no PyPI for now), one source for the version, CHANGELOG.md (Keep a Changelog), CI that tests on push/PR and publishes a GitHub Release on a tag, new `awa version` / `awa versions` / `awa update [--to vX.Y.Z] [--yes]` commands that detect uv or pipx, and a README section for versions and the maintainer's release steps."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install a known version (Priority: P1)

A user installs a specific, named release of awa (e.g. `v0.1.0`) instead of "whatever is on
main today", and can tell afterwards which version they have.

**Why this priority**: Every other story depends on releases existing as named, stable points.
Without them, updating and downgrading have nothing to point at.

**Independent Test**: Tag a release, install it by its tag in a clean environment, and check
that the reported version equals the tag.

**Acceptance Scenarios**:

1. **Given** release `v0.1.0` exists, **When** the user installs awa pinned to `v0.1.0`,
   **Then** `awa --version` and `awa version` report `0.1.0`.
2. **Given** a newer commit is on main but not released, **When** the user installs `v0.1.0`,
   **Then** they get exactly the `v0.1.0` code, not the newer commit.
3. **Given** the maintainer changes the version number, **When** they look for where to change
   it, **Then** there is exactly one place.

---

### User Story 2 - Update and downgrade from awa itself (Priority: P1)

The user runs `awa update` to move to the newest release, or `awa update --to v0.1.0` to move to
a specific (possibly older) release, without having to remember installer commands.

**Why this priority**: This is the user's explicit requirement: update and downgrade must work
from awa, not only through the installer.

**Independent Test**: Install an older release with uv (and separately with pipx), run
`awa update`, and check the newest version is installed; then run `awa update --to <older>`,
confirm, and check the older version is installed.

**Acceptance Scenarios**:

1. **Given** awa was installed with uv or pipx and a newer release exists, **When** the user runs
   `awa update`, **Then** awa shows the current and target version, reinstalls itself at the
   newest release using the same installer, and reports the new version.
2. **Given** the user is on the newest release, **When** they run `awa update`, **Then** awa says
   it is already up to date and changes nothing.
3. **Given** the user runs `awa update --to v0.1.0` while on a newer version, **When** awa asks
   "Downgrade from X to 0.1.0?", **Then** it proceeds only on "y"; any other answer cancels with
   nothing changed.
4. **Given** the user adds `--yes`, **When** they downgrade, **Then** no question is asked.
5. **Given** the user passes a version that was never released (e.g. `--to v9.9.9`), **Then** awa
   says that version does not exist, lists how to see available versions, and changes nothing.
6. **Given** `--to 0.1.0` (no leading "v"), **Then** it is treated the same as `--to v0.1.0`.
7. **Given** awa was not installed by uv or pipx (e.g. run from a development checkout), **When**
   the user runs `awa update`, **Then** awa does not try to change anything and prints the exact
   command(s) to run by hand.
8. **Given** the reinstall fails, **Then** awa shows the installer's error and exits with a
   non-zero status; the previous installation is left as the installer leaves it.

---

### User Story 3 - See current and available versions (Priority: P2)

The user runs `awa version` to see the installed version and whether a newer release exists, and
`awa versions` to list all releases, newest first.

**Why this priority**: Useful to decide whether and where to update or downgrade, but update works
without it.

**Independent Test**: With two releases published, run both commands and compare the output with
the release list.

**Acceptance Scenarios**:

1. **Given** the installed version is older than the newest release, **When** the user runs
   `awa version`, **Then** it shows both versions and suggests `awa update`.
2. **Given** the installed version is the newest, **Then** `awa version` says it is up to date.
3. **Given** there is no network, **Then** `awa version` still shows the installed version and says
   the latest version could not be checked; the exit status is zero.
4. **Given** releases exist, **When** the user runs `awa versions`, **Then** they are listed newest
   first, with the installed one marked.

---

### User Story 4 - Maintainer cuts a release (Priority: P2)

The maintainer bumps the version, adds a changelog entry, tags the commit, and pushes the tag.
Automation tests the code, builds the package, and publishes a release with that version's
changelog notes and the built files attached.

**Why this priority**: Makes releases repeatable and safe, but a release can be cut by hand.

**Independent Test**: Push a tag on a fork or test repository and check the release appears with
notes and files; push a tag that does not match the version and check that it is refused.

**Acceptance Scenarios**:

1. **Given** code is pushed or a pull request is opened, **Then** the automated tests run and the
   result is visible on the commit or pull request.
2. **Given** the maintainer pushes tag `vX.Y.Z` matching the package version, **When** the tests
   pass, **Then** a release named `vX.Y.Z` is published with the changelog section for `X.Y.Z` as
   its notes and the built package files attached.
3. **Given** the tag does not match the package version, **Then** no release is published and the
   failure says why.
4. **Given** the tests fail on a tag, **Then** no release is published.

---

### User Story 5 - Documentation for versions (Priority: P2)

The README explains how to install a specific version, update, downgrade, check the installed
version, and (for the maintainer) how to cut a release. A changelog lists what changed in each
release.

**Why this priority**: Without it, users won't find the commands; required by the user.

**Independent Test**: Follow the README's version section on a clean machine, step by step.

**Acceptance Scenarios**:

1. **Given** a new user reads the README, **Then** they find the install-a-version, update,
   downgrade and check-version steps, using both `awa` commands and the plain installer commands.
2. **Given** a release is published, **Then** the changelog has an entry for it with its date.

---

### Edge Cases

- A folder literally named `version`, `versions` or `update`: `awa version` runs the command;
  `awa ./version` opens the folder. The README mentions this.
- No network, a timeout, or the release service rate-limits the request: a clear one-line message
  ("Could not reach GitHub to check releases: …"), non-zero exit for `update` and `versions`,
  zero for `version` (it still shows the installed version).
- awa servers are running while updating: awa warns that running servers keep the old version
  until restarted. Detection is best effort; the warning is always printed after a successful
  update.
- The installed version is newer than every release (e.g. a dev install from main): `awa version`
  says so; `awa update` treats moving to the newest release as a downgrade and asks to confirm.
- Both uv and pipx are on the machine: awa uses the one that actually installed it.
- The installer command itself is missing from `PATH` even though it installed awa: awa prints the
  manual command instead.
- Tags that are not valid versions (e.g. `test`, `v1.0.0-rc1`): ignored for "latest"; pre-releases
  are out of scope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Releases MUST be identified by Semantic Versioning tags of the form `vMAJOR.MINOR.PATCH`;
  the first release is `v0.1.0`, made from the current main.
- **FR-002**: The version number MUST be defined in exactly one place in the source; everything that
  reports the version (including `awa --version`) MUST read it from there.
- **FR-003**: A pinned install of a release (installer pointed at the tag) MUST install exactly that
  release's code.
- **FR-004**: The repository MUST have a `CHANGELOG.md` in Keep a Changelog format, with an
  "Unreleased" section and one dated section per release.
- **FR-005**: Automated checks MUST run the test suite on every push and pull request.
- **FR-006**: On pushing a version tag, automation MUST: verify the tag matches the package
  version, run the tests, build the wheel and source distribution, and publish a release named after
  the tag with that version's changelog section as notes and the built files attached. Any failure
  MUST stop the release.
- **FR-007**: `awa version` MUST print the installed version and, when reachable, the newest
  release and whether an update is available.
- **FR-008**: `awa versions` MUST list released versions newest first and mark the installed one.
- **FR-009**: `awa update` MUST move to the newest release; `awa update --to VERSION` MUST move to
  the given release, accepting it with or without a leading `v`.
- **FR-010**: Moving to an older version MUST ask for confirmation unless `--yes` is given;
  a non-interactive session without `--yes` MUST refuse a downgrade with a message.
- **FR-011**: `awa update` MUST detect whether awa was installed by uv or pipx and reinstall with the
  same tool at the requested tag; otherwise it MUST change nothing and print the exact manual
  command(s).
- **FR-012**: `awa update` MUST refuse unknown versions and do nothing when already on the requested
  version, with a clear message in each case.
- **FR-013**: After a successful update, awa MUST print the new version and a note that running awa
  servers must be restarted.
- **FR-014**: The subcommands `version`, `versions` and `update` MUST take precedence over a folder
  argument of the same name; any path containing a `/` (e.g. `./version`) MUST open the folder.
  Existing usage (`awa`, `awa path`, `--port`, `--no-browser`, `--version`) MUST keep working.
- **FR-015**: Checking releases MUST use only the Python standard library at runtime, with a short
  timeout (about 10 seconds) and no authentication required.
- **FR-016**: The README MUST have a versions section covering: install a specific version, update,
  downgrade, check the installed version (with `awa` and with plain uv/pipx commands), and the
  maintainer's release steps.
- **FR-017**: PyPI publishing MUST be recorded in the README's Parked list, not built.

### Key Entities

- **Release**: a published version; has a version number (`X.Y.Z`), a tag (`vX.Y.Z`), a date,
  changelog notes, and attached package files.
- **Installation**: how awa is installed on this machine; has an installed version and an installer
  (uv, pipx, or other).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can move to any published release (newer or older) with one `awa` command plus
  at most one confirmation, in under 1 minute on a normal connection.
- **SC-002**: After any update or downgrade, the reported version equals the requested release in
  100% of tested cases (uv and pipx, up and down).
- **SC-003**: A maintainer cuts a release in at most 4 manual steps (bump version, edit changelog,
  commit, tag and push); everything else is automatic.
- **SC-004**: A tag whose version does not match the package never produces a published release.
- **SC-005**: With no network, every new command finishes within about 15 seconds with a readable
  message and no traceback.
- **SC-006**: All existing tests still pass and the new behaviour (argument routing, version parsing
  and ordering, installer detection, update decisions, offline handling) is covered by automated
  tests that need no network.

## Assumptions

- Releases are hosted on GitHub only (repository `adiacov/ai-web-assist`); PyPI is parked.
- Installation and updates go through uv or pipx installing from the git repository at a tag; both
  already support installing from a git URL at a tag.
- Unauthenticated access to GitHub's public release/tag listing is enough for this usage (low
  request rate).
- Pre-release versions (e.g. `-rc1`) are out of scope.
- awa does not stop running servers itself; it only warns.
- Windows remains unsupported, as in the MVP.
