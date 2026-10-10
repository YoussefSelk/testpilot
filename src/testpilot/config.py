"""Validated YAML configuration and path resolution."""

import os
from pathlib import Path

import yaml
from pydantic import ValidationError

from testpilot.models import Configuration, ResolvedRepository, Settings


class ConfigError(ValueError):
    pass


def load_config(path: Path) -> Configuration:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Configuration.model_validate(data)
    except ValidationError as exc:
        # Pydantic input values may contain secrets; report locations and reasons only.
        errors = "; ".join(
            f"{'.'.join(map(str, e['loc'])) or 'configuration'}: {e['msg']}"
            for e in exc.errors(include_input=False, include_context=False)
        )
        raise ConfigError(errors) from None
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise ConfigError(f"Cannot load configuration {path}: {type(exc).__name__}") from None


def resolve(
    config: Configuration,
    config_path: Path,
    environment: str | None = None,
    *,
    parallel: int | None = None,
    timeout: float | None = None,
    report_dir: str | None = None,
    repo_names: list[str] | None = None,
) -> Settings:
    base = config_path.resolve().parent
    if environment is not None and environment not in config.profiles:
        raise ConfigError(f"Unknown environment profile: {environment}")
    profile = config.profiles.get(environment or "")
    workers = (
        parallel
        if parallel is not None
        else (
            profile.parallel
            if profile and profile.parallel is not None
            else config.defaults.parallel
        )
    )
    if workers < 1 or workers > 256:
        raise ConfigError("Parallel workers must be between 1 and 256")
    output = report_dir or (profile.report_dir if profile else None) or config.defaults.report_dir
    directory = (base / output).resolve()
    requested = set(repo_names or [])
    unknown = requested - {r.name for r in config.repositories}
    if unknown:
        raise ConfigError(f"Unknown repositories: {', '.join(sorted(unknown))}")
    resolved: list[ResolvedRepository] = []
    outputs: set[Path] = set()
    for repo in config.repositories:
        if requested and repo.name not in requested:
            continue
        path = (base / repo.path).resolve()
        cwd = (path / (repo.working_dir or ".")).resolve()
        if not path.is_dir() or not cwd.is_dir():
            raise ConfigError(f"Repository {repo.name}: directory does not exist: {cwd}")
        junit = (cwd / repo.junit).resolve() if repo.junit else None
        if junit:
            if junit in outputs:
                raise ConfigError(f"Repositories share a JUnit output path: {junit}")
            if junit.exists() and not junit.is_file():
                raise ConfigError(f"JUnit output must be a file: {junit}")
            outputs.add(junit)
        seconds = timeout if timeout is not None else repo.timeout
        if seconds is None:
            seconds = (profile.timeout if profile else None) or config.defaults.timeout
        import math

        if not math.isfinite(seconds) or seconds <= 0:
            raise ConfigError("Timeout must be positive and finite")
        env = {**os.environ, **config.defaults.env, **(profile.env if profile else {}), **repo.env}
        resolved.append(ResolvedRepository(repo.name, path, cwd, repo.command, seconds, env, junit))
    return Settings(environment or "default", workers, directory, resolved)
