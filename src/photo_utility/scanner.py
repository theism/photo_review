from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .filenames import is_image_file, parse_commcare_filename, PhotoMeta


def scan_directory_for_photos(root: Path) -> Tuple[List[PhotoMeta], List[Path]]:
    valid: List[PhotoMeta] = []
    invalid: List[Path] = []
    for path in root.iterdir():
        if not is_image_file(path):
            continue
        meta = parse_commcare_filename(path)
        if meta is None:
            invalid.append(path)
        else:
            valid.append(meta)
    return valid, invalid


def group_by_question_id(metas: Iterable[PhotoMeta]) -> Dict[str, List[PhotoMeta]]:
    groups: Dict[str, List[PhotoMeta]] = defaultdict(list)
    for meta in metas:
        groups[meta.question_id].append(meta)
    return groups


def group_by_form_id(metas: Iterable[PhotoMeta]) -> Dict[str, List[PhotoMeta]]:
    groups: Dict[str, List[PhotoMeta]] = defaultdict(list)
    for meta in metas:
        groups[meta.form_id].append(meta)
    return groups
