"""Safe project discovery and file access for Forge Guard workspaces."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterator

from app.schemas.workspace import ProjectFile, ProjectManifest, ProjectReference

IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "dist",
    "build",
    ".idea",
    ".vscode",
}

SENSITIVE_FILE_NAMES = {
    ".env",
}

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".md": "markdown",
    ".json": "json",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".txt": "text",
    ".cfg": "config",
    ".ini": "config",
}


def _is_sensitive_file(name: str) -> bool:
    if name in SENSITIVE_FILE_NAMES:
        return True
    if name.startswith(".env.") or name.startswith(".env-"):
        return True
    return False


def _is_within(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    return resolved == root or root in resolved.parents


class WorkspaceError(Exception):
    """Raised when a workspace operation cannot be completed safely."""


class WorkspaceService:
    """Manage projects confined to a single server-side workspace root."""

    def __init__(
        self,
        root: str | Path,
        max_file_size_bytes: int | None = None,
    ) -> None:
        if max_file_size_bytes is None:
            env_value = os.environ.get("FORGE_MAX_FILE_SIZE_BYTES")
            max_file_size_bytes = (
                int(env_value) if env_value else 1_048_576
            )
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_file_size_bytes = max_file_size_bytes
        self._projects: dict[str, ProjectReference] = {}
        self._project_paths: dict[str, Path] = {}

    def _resolve(self, relative: str | Path | None) -> Path:
        if relative is None or str(relative).strip() == "":
            relative = "."
        candidate = (self.root / relative).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise WorkspaceError("Path is outside the configured workspace root.")
        return candidate

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def _project_id(self, relative_path: str) -> str:
        digest = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:12]
        return f"project-{digest}"

    def register_project(
        self, relative_path: str | Path = ".", name: str | None = None
    ) -> ProjectReference:
        resolved = self._resolve(relative_path)
        if not resolved.exists():
            raise WorkspaceError("Project path does not exist.")
        if not resolved.is_dir():
            raise WorkspaceError("Project path is not a directory.")
        relative = resolved.relative_to(self.root).as_posix()
        if relative == ".":
            relative = ""
        project_id = self._project_id(relative if relative else ".")
        display_name = name or (resolved.name if resolved != self.root else "workspace")
        reference = ProjectReference(
            project_id=project_id,
            name=display_name,
            relative_path=relative if relative else ".",
        )
        self._projects[project_id] = reference
        self._project_paths[project_id] = resolved
        return reference

    def _recover(self, project_id: str) -> bool:
        """Re-register a top-level project dir whose deterministic id matches."""
        try:
            entries = sorted(self.root.iterdir())
        except OSError:
            return False
        for entry in entries:
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            if self._project_id(entry.name) == project_id:
                try:
                    self.register_project(entry.name)
                except WorkspaceError:
                    return False
                return True
        return False

    def get_project(self, project_id: str) -> ProjectReference:
        if project_id not in self._projects and not self._recover(project_id):
            raise WorkspaceError("Unknown project.")
        return self._projects[project_id]

    def project_root(self, project_id: str) -> Path:
        if project_id not in self._project_paths and not self._recover(project_id):
            raise WorkspaceError("Unknown project.")
        return self._project_paths[project_id]

    def _ignored(self, path: Path) -> bool:
        return path.name in IGNORED_DIRECTORIES

    def iter_files(self, project_id: str) -> list[ProjectFile]:
        root = self.project_root(project_id)
        results: list[ProjectFile] = []
        for file_path in self._walk(root):
            relative = file_path.relative_to(root).as_posix()
            metadata = self._metadata(file_path, relative, root)
            results.append(metadata)
        results.sort(key=lambda item: item.path)
        return results

    def _walk(self, root: Path) -> Iterator[Path]:
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = sorted(
                name for name in dirnames if name not in IGNORED_DIRECTORIES
            )
            for filename in sorted(filenames):
                if _is_sensitive_file(filename):
                    continue
                yield Path(dirpath) / filename

    def _metadata(
        self, file_path: Path, relative: str, root: Path
    ) -> ProjectFile:
        suffix = file_path.suffix.lower()
        language = LANGUAGE_BY_SUFFIX.get(suffix)
        if suffix == ".py":
            language = "python"

        if _is_sensitive_file(file_path.name):
            return ProjectFile(
                path=relative,
                language=language,
                size_bytes=0,
                sha256=None,
                readable=False,
                error="Excluded sensitive configuration file.",
            )

        # Containment check for symlinks and resolved paths.
        if not _is_within(file_path, self.root):
            return ProjectFile(
                path=relative,
                language=language,
                size_bytes=0,
                sha256=None,
                readable=False,
                error="Path is outside the configured workspace root.",
            )
        resolved = file_path.resolve()
        if resolved != file_path and not _is_within(resolved, root):
            return ProjectFile(
                path=relative,
                language=language,
                size_bytes=0,
                sha256=None,
                readable=False,
                error="Symlink target is outside the project root.",
            )

        try:
            stat = file_path.stat()
            size = stat.st_size
        except OSError as error:
            return ProjectFile(
                path=relative, language=language, readable=False, error=str(error)
            )

        if size > self.max_file_size_bytes:
            return ProjectFile(
                path=relative,
                language=language,
                size_bytes=size,
                sha256=None,
                readable=False,
                error=(
                    f"File exceeds configured size limit "
                    f"({self.max_file_size_bytes} bytes)."
                ),
            )

        sha256 = None
        readable = True
        error = None
        try:
            with file_path.open("rb") as handle:
                sha256 = hashlib.sha256(handle.read()).hexdigest()
        except OSError as read_error:
            readable = False
            error = str(read_error)
        return ProjectFile(
            path=relative,
            language=language,
            size_bytes=size,
            sha256=sha256,
            readable=readable,
            error=error,
        )

    def read_file(self, project_id: str, relative_path: str) -> str:
        root = self.project_root(project_id)
        resolved = (root / relative_path).resolve()
        if resolved != root and root not in resolved.parents:
            raise WorkspaceError("Path is outside the project root.")
        if not resolved.exists() or not resolved.is_file():
            raise WorkspaceError("File does not exist.")
        if resolved.is_symlink():
            if not _is_within(resolved, root):
                raise WorkspaceError("Symlink target is outside the project root.")
        try:
            size = resolved.stat().st_size
        except OSError as error:
            raise WorkspaceError(f"Unable to stat file: {error}") from error
        if size > self.max_file_size_bytes:
            raise WorkspaceError(
                f"File exceeds configured size limit ({self.max_file_size_bytes} bytes)."
            )
        try:
            raw = resolved.read_bytes()
        except OSError as error:
            raise WorkspaceError(f"Unable to read file: {error}") from error
        if b"\x00" in raw:
            raise WorkspaceError("File appears to be binary and cannot be read as text.")
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise WorkspaceError(f"Unable to read file: {error}") from error

    def manifest(self, project_id: str) -> ProjectManifest:
        reference = self.get_project(project_id)
        files = self.iter_files(project_id)
        python_count = sum(1 for f in files if f.language == "python")
        return ProjectManifest(
            project_id=reference.project_id,
            name=reference.name,
            relative_path=reference.relative_path,
            file_count=len(files),
            python_file_count=python_count,
            files=files,
            ignored_directories=sorted(IGNORED_DIRECTORIES),
        )
