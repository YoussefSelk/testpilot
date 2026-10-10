# Configuration reference


```yaml
version: 1
defaults:
  timeout: 300
  parallel: 2
  report_dir: reports
  env:
    APP_ENV: local
profiles:
  ci:
    timeout: 600
    parallel: 4
    report_dir: reports/ci
    env:
      APP_ENV: test
repositories:
  - name: backend
    path: examples/repo_a
    working_dir: .
    command: [python, -m, pytest, tests/, -q, --junitxml=test-results.xml]
    timeout: 120
    env:
      FEATURE_MODE: test
    junit: test-results.xml
```

| Field | Meaning |
| --- | --- |
| `version` | Required schema version, currently `1` |
| `defaults.timeout` | Positive finite seconds; default `300` |
| `defaults.parallel` | Workers from `1` to `256`; default `2` |
| `defaults.report_dir` | Output directory relative to the config; default `reports` |
| `defaults.env` | String environment variables layered over inherited variables |
| `profiles` | Named overrides of defaults and environment variables |
| `repositories` | Nonempty ordered list of repository settings |
| `name` | Unique identifier using letters, digits, `_`, `.` and `-`; starts with a letter/digit |
| `path` | Existing directory; relative to the config file or absolute |
| `command` | Nonempty list of program arguments; shell strings are rejected |
| `working_dir` | Existing directory relative to `path`, or an absolute directory |
| `timeout` | Optional repository timeout |
| `env` | Optional repository environment overrides; YAML values must be strings |
| `junit` | Optional XML file relative to the working directory, or absolute |

Unknown keys and unknown profile/repository selections are errors. The command
must produce the configured XML: **setting `junit` does not add command flags**.
TestPilot clears the previous configured JUnit file before execution to avoid
stale results. Use a dedicated generated file, never a source file. Repositories
in a run cannot share the same resolved JUnit output path.

Environment precedence, from lowest to highest: inherited process environment,
`defaults.env`, profile `env`, repository `env`. For timeout: defaults, profile,
repository, CLI `--timeout`. For parallelism and output directory: defaults,
profile, CLI. There are no repository-specific worker/report-directory settings.
Without `--env`, defaults apply and the report environment is `default`.

Environment values are not printed by TestPilot. Supply real secrets through
your environment or CI secret store; examples contain none. Captured test logs
can contain whatever the test programs print, so review reports before sharing.

## Environment profiles


The main example provides `local`, `development`, `staging` and `ci`:

```bash
testpilot run --env development
testpilot run --env staging --parallel 1
testpilot run --env ci --parallel 4
```

Profiles override variables and defaults only; repository-specific settings
remain higher priority. TestPilot does not provision environments or dependencies.

## Operating limits


- Local repositories only; no cloning, dependency installation or remote runners.
- One JUnit file per repository. Summary-only XML without testcase evidence is
  incomplete; dialects with inconsistent declared counters are rejected.
- Commands and repositories are trusted local code; subprocess isolation is not
  a sandbox. Output is captured to temporary files, then loaded into reports.
- Avoid simultaneous TestPilot invocations against the same JUnit locations:
  unique consolidated run directories do not isolate repository-generated files.
- No distributed scheduling, retry policy, streamed logs or report dashboard.
- GitLab/Jenkins require their respective hosted environments; file presence
  and local shared-script checks are distinct from a hosted pipeline run.

