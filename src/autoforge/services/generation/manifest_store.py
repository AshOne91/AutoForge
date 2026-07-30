import json
from pathlib import Path, PurePosixPath
from typing import Final

from pydantic import BaseModel, ValidationError

from autoforge.core.generation import GenerationManifest
from autoforge.core.job import GenerationJobManifest, ManifestDocumentKind
from autoforge.core.workspace import Workspace

MANIFEST_RELATIVE_PATH: Final = PurePosixPath(".autoforge", "manifest.json")
TEMP_MANIFEST_RELATIVE_PATH: Final = PurePosixPath(
    ".autoforge",
    "manifest.json.tmp",
)
type StoredManifest = GenerationManifest | GenerationJobManifest


class ManifestStoreError(RuntimeError):
    """Manifest를 안전하게 저장하거나 읽을 수 없을 때 발생한다."""


class ManifestStore:
    """Workspace 내부의 고정 경로에 GenerationManifest를 저장한다."""

    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    @property
    def path(self) -> Path:
        return self._workspace.resolve(MANIFEST_RELATIVE_PATH)

    def save(self, manifest: GenerationManifest) -> Path:
        return self._save(manifest)

    def save_job(self, manifest: GenerationJobManifest) -> Path:
        return self._save(manifest)

    def _save(self, manifest: BaseModel) -> Path:
        target = self.path
        temporary = self._workspace.resolve(TEMP_MANIFEST_RELATIVE_PATH)
        self._validate_write_targets(target, temporary)
        serialized = self._serialize(manifest)

        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            temporary.write_bytes(serialized)
            temporary.replace(target)
        except OSError as error:
            raise ManifestStoreError(
                f"Manifest를 저장하지 못했습니다: {target}"
            ) from error
        finally:
            if temporary.is_file():
                temporary.unlink()
        return target

    def load(self) -> GenerationManifest:
        manifest = self.load_any()
        if not isinstance(manifest, GenerationManifest):
            raise ManifestStoreError(f"기존 GenerationManifest가 아닙니다: {self.path}")
        return manifest

    def load_job(self) -> GenerationJobManifest:
        manifest = self.load_any()
        if not isinstance(manifest, GenerationJobManifest):
            raise ManifestStoreError(f"GenerationJobManifest가 아닙니다: {self.path}")
        return manifest

    def load_any(self) -> StoredManifest:
        target = self.path
        if not target.is_file():
            raise ManifestStoreError(f"Manifest 파일을 찾을 수 없습니다: {target}")

        try:
            data = json.loads(target.read_bytes())
            if not isinstance(data, dict):
                raise TypeError("Manifest 최상위 값은 객체여야 합니다.")

            document_kind = data.get("document_kind")
            if document_kind is None:
                if "format_version" in data:
                    raise ValueError("Manifest 문서 종류가 없습니다.")
                return GenerationManifest.model_validate(data)
            if document_kind != ManifestDocumentKind.GENERATION_JOB:
                raise ValueError(f"알 수 없는 Manifest 문서 종류: {document_kind}")
            return GenerationJobManifest.model_validate(data)
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as error:
            raise ManifestStoreError(
                f"Manifest 파일이 유효하지 않습니다: {target}"
            ) from error
        except (TypeError, ValueError) as error:
            raise ManifestStoreError(
                f"Manifest 파일이 유효하지 않습니다: {target}"
            ) from error

    @staticmethod
    def _serialize(manifest: BaseModel) -> bytes:
        data = manifest.model_dump(mode="json")
        content = json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        return f"{content}\n".encode()

    @staticmethod
    def _validate_write_targets(target: Path, temporary: Path) -> None:
        if target.exists() and not target.is_file():
            raise ManifestStoreError(f"Manifest 경로가 파일이 아닙니다: {target}")
        if temporary.exists() and not temporary.is_file():
            raise ManifestStoreError(
                f"임시 Manifest 경로가 파일이 아닙니다: {temporary}"
            )
        if target.parent.exists() and not target.parent.is_dir():
            raise ManifestStoreError(
                f"Manifest 부모 경로가 디렉터리가 아닙니다: {target.parent}"
            )
