from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Optional


# Original format: after_the_right_fit-deliver_photograph-1sf5k8cx9fu0iwjs9k45-form_1afa2004-ba50-468e-af42-7493974ef164
COMMCARE_FILENAME_RE = re.compile(
    r"^(?P<json_block>[a-z0-9_\-]+)-(?P<question_id>[a-z0-9_\-]+)-(?P<user_id>[a-z0-9]+)-form_(?P<form_id>[a-f0-9\-]{36})$",
    re.IGNORECASE,
)

# New format with prefix: 6accdb14457aadff034d-abass kamara-muac_group-muac_display_group_1-muac_photo-6accdb14457aadff034d-form_12fff2a8-ba62-4c37-b703-e74358e4a48e
COMMCARE_FILENAME_WITH_PREFIX_RE = re.compile(
    r"^[^-]+-[^-]+-(?P<json_block>[a-z0-9_\-]+)-(?P<question_id>[a-z0-9_\-]+)-(?P<user_id>[a-z0-9]+)-form_(?P<form_id>[a-f0-9\-]{36})$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PhotoMeta:
    json_block: str
    question_id: str
    user_id: str
    form_id: str
    extension: str
    filename: str
    filepath: Path


def strip_extension(filename: str) -> tuple[str, str]:
    p = Path(filename)
    stem = p.stem
    ext = p.suffix.lower().lstrip(".")
    return stem, ext


def parse_commcare_filename(path: Path) -> Optional[PhotoMeta]:
    stem, ext = strip_extension(path.name)
    
    # Try original format first
    match = COMMCARE_FILENAME_RE.match(stem)
    if match:
        groups = match.groupdict()
        return PhotoMeta(
            json_block=groups["json_block"],
            question_id=groups["question_id"],
            user_id=groups["user_id"],
            form_id=groups["form_id"],
            extension=ext,
            filename=path.name,
            filepath=path,
        )
    
    # Try new format with prefix
    match = COMMCARE_FILENAME_WITH_PREFIX_RE.match(stem)
    if match:
        groups = match.groupdict()
        return PhotoMeta(
            json_block=groups["json_block"],
            question_id=groups["question_id"],
            user_id=groups["user_id"],
            form_id=groups["form_id"],
            extension=ext,
            filename=path.name,
            filepath=path,
        )
    
    return None


IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower().lstrip(".") in IMAGE_EXTENSIONS
