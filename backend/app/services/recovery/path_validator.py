import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Tuple

from app.models.recovery import DestinationType, OverwritePolicy


class PathValidationError(Exception):
    """Raised when a restoration target path violates security or sandbox boundaries."""
    pass


def get_vaultguard_root() -> str:
    cwd = os.path.abspath(os.getcwd())
    if os.path.basename(cwd).lower() == "backend":
        return os.path.dirname(cwd)
    return cwd


class SafePathValidator:
    """
    Validates and sanitizes restoration target paths.
    Guarantees protection against directory traversal (../), absolute path hijacking,
    and symlink redirection attacks.
    """

    DEFAULT_SAFE_ROOT = os.path.abspath(os.path.join(get_vaultguard_root(), "recovered_files"))
    STAGING_ROOT = os.path.abspath(os.path.join(get_vaultguard_root(), ".recovery_staging"))

    def __init__(self, safe_root: Optional[str] = None):
        self.safe_root = os.path.abspath(safe_root or self.DEFAULT_SAFE_ROOT)
        os.makedirs(self.safe_root, exist_ok=True)
        os.makedirs(self.STAGING_ROOT, exist_ok=True)

    def validate_and_resolve_destination(
        self,
        original_file_path: str,
        destination_path: Optional[str] = None,
        destination_type: str = DestinationType.SAFE_DIR.value,
        organization_id: Optional[str] = None,
    ) -> str:
        """
        Derives an authorized absolute disk path for the restored file.
        Rejects path traversal, null bytes, and writes outside permitted root boundaries.
        Automatically creates target directories (e.g. recovered_files/).
        """
        if not original_file_path or "\x00" in original_file_path:
            raise PathValidationError("Invalid original file path: contains null bytes or empty value.")

        # Normalize relative path by stripping leading drive letters or root slashes
        clean_rel = original_file_path.replace("\\", "/")
        if ":" in clean_rel:
            clean_rel = clean_rel.split(":", 1)[1]
        clean_rel = clean_rel.lstrip("/")

        # Check for traversal patterns
        parts = Path(clean_rel).parts
        if ".." in parts:
            raise PathValidationError(f"Path traversal detected in file path: {original_file_path}")

        if destination_type == DestinationType.ORIGINAL.value:
            # Reconstruct original location if safe
            norm_dest = os.path.abspath(original_file_path)
            norm_lower = norm_dest.lower()
            prohibited_roots = (
                "c:\\windows", "c:\\boot", "c:\\etc", "c:\\bin", "c:\\sbin", "c:\\usr",
                "/etc", "/bin", "/sbin", "/usr", "\\etc", "\\bin", "\\usr", "\\sbin",
            )
            # Ensure it doesn't escape to critical OS directories
            if any(norm_lower.startswith(p) for p in prohibited_roots) or any(part.lower() in ("windows", "system32", "etc", "bin", "sbin") for part in Path(norm_dest).parts[:2]):
                raise PathValidationError(f"Restoration to critical OS path is prohibited: {original_file_path}")
            os.makedirs(os.path.dirname(norm_dest), exist_ok=True)
            return norm_dest

        # Determine target safe directory root
        if destination_type == DestinationType.CUSTOM_SAFE_DIR.value and destination_path:
            norm_custom = os.path.abspath(destination_path)
            # Ensure custom destination does not contain traversal
            if ".." in Path(destination_path).parts:
                raise PathValidationError("Path traversal detected in custom destination path.")
            base_dir = norm_custom
        else:
            base_dir = self.safe_root

        os.makedirs(base_dir, exist_ok=True)
        # Restore directly under base_dir with file's basename
        file_basename = os.path.basename(original_file_path.replace("\\", "/"))
        target_file_path = os.path.abspath(os.path.join(base_dir, file_basename))

        # Enforce that target is strictly inside base_dir
        common = os.path.commonpath([base_dir, target_file_path])
        if os.path.abspath(common) != os.path.abspath(base_dir):
            raise PathValidationError(
                f"Destination path escapes the authorized boundary: '{target_file_path}'"
            )

        return target_file_path

    def resolve_file_conflict(
        self,
        target_path: str,
        overwrite_policy: str = OverwritePolicy.SKIP.value,
    ) -> Tuple[bool, str]:
        """
        Inspects whether target already exists on disk and resolves collision according to policy.
        Returns: (should_write, final_path)
        """
        if not os.path.exists(target_path):
            return True, target_path

        if overwrite_policy == OverwritePolicy.SKIP.value:
            return False, target_path

        if overwrite_policy == OverwritePolicy.OVERWRITE.value:
            return True, target_path

        if overwrite_policy == OverwritePolicy.RENAME.value:
            # Generate collision-free filename: "file (1).ext", "file (2).ext"
            dirname, filename = os.path.split(target_path)
            stem, ext = os.path.splitext(filename)
            counter = 1
            while True:
                candidate = os.path.join(dirname, f"{stem} ({counter}){ext}")
                if not os.path.exists(candidate):
                    return True, candidate
                counter += 1

        raise PathValidationError(f"Unrecognized overwrite policy: {overwrite_policy}")

    def create_staging_path(self, job_id: uuid.UUID, file_version_id: uuid.UUID) -> str:
        """Creates an isolated staging filepath for holding verified payload before final placement."""
        job_dir = os.path.join(self.STAGING_ROOT, str(job_id))
        os.makedirs(job_dir, exist_ok=True)
        return os.path.join(job_dir, f"{file_version_id}.tmp")

    def commit_staged_file(self, staging_path: str, target_path: str) -> None:
        """Safely moves a verified staged file into its final authorized destination."""
        if not os.path.exists(staging_path):
            raise FileNotFoundError(f"Staged file missing: '{staging_path}' not found.")

        target_dir = os.path.dirname(target_path)
        try:
            os.makedirs(target_dir, exist_ok=True)
        except PermissionError as e:
            raise PermissionError(f"Permission denied: unable to create destination directory '{target_dir}'.")
        except Exception as e:
            raise OSError(f"Destination folder error: cannot create '{target_dir}': {str(e)}")

        try:
            shutil.copy2(staging_path, target_path)
            try:
                os.remove(staging_path)
            except Exception:
                pass
        except PermissionError:
            raise PermissionError(f"Permission denied: unable to write to '{target_path}'.")
        except Exception as e:
            raise OSError(f"File write failed: unable to write restored file to '{target_path}': {str(e)}")

    def cleanup_staging_dir(self, job_id: uuid.UUID) -> None:
        """Removes the entire temporary staging directory for a recovery job."""
        job_dir = os.path.join(self.STAGING_ROOT, str(job_id))
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir, ignore_errors=True)


path_validator = SafePathValidator()
