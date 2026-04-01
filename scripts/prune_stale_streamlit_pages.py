#!/usr/bin/env python3

import argparse
import re
import subprocess
import sys
from pathlib import Path


def infer_slug(path: Path) -> str:
    stem = path.stem
    return re.sub(r"^\d+_", "", stem)


def load_tracked_pages(repo_dir: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "ls-files", "--", "pages"],
        capture_output=True,
        text=True,
        check=True,
    )
    tracked: list[Path] = []
    for line in result.stdout.splitlines():
        if line.startswith("pages/") and line.endswith(".py"):
            tracked.append(Path(line))
    return tracked


def find_tracked_slug_collisions(tracked_pages: list[Path]) -> dict[str, list[Path]]:
    collisions: dict[str, list[Path]] = {}
    slug_map: dict[str, list[Path]] = {}
    for rel_path in tracked_pages:
        slug_map.setdefault(infer_slug(rel_path), []).append(rel_path)

    for slug, paths in slug_map.items():
        if len(paths) > 1:
            collisions[slug] = sorted(paths)
    return collisions


def find_stale_collision_files(repo_dir: Path, tracked_pages: list[Path]) -> list[tuple[str, Path, Path]]:
    pages_dir = repo_dir / "pages"
    tracked_set = {str(path) for path in tracked_pages}
    tracked_by_slug = {infer_slug(path): path for path in tracked_pages}
    stale_collisions: list[tuple[str, Path, Path]] = []

    for actual_path in sorted(pages_dir.glob("*.py")):
        rel_path = actual_path.relative_to(repo_dir)
        rel_path_str = str(rel_path)
        if rel_path_str in tracked_set:
            continue

        stale_slug = infer_slug(rel_path)
        tracked_match = tracked_by_slug.get(stale_slug)
        if tracked_match is not None:
            stale_collisions.append((stale_slug, rel_path, tracked_match))

    return stale_collisions


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune stale Streamlit page files that collide with tracked pathnames.")
    parser.add_argument("--repo-dir", default=".", help="Path to the repo root")
    parser.add_argument("--apply", action="store_true", help="Delete stale colliding files")
    args = parser.parse_args()

    repo_dir = Path(args.repo_dir).resolve()
    tracked_pages = load_tracked_pages(repo_dir)

    tracked_collisions = find_tracked_slug_collisions(tracked_pages)
    if tracked_collisions:
        print("Tracked Streamlit page pathname collisions found:", file=sys.stderr)
        for slug, paths in tracked_collisions.items():
            joined = ", ".join(str(path) for path in paths)
            print(f"  - {slug}: {joined}", file=sys.stderr)
        return 1

    stale_collisions = find_stale_collision_files(repo_dir, tracked_pages)
    if not stale_collisions:
        print("No stale colliding Streamlit page files found.")
        return 0

    action = "Deleting" if args.apply else "Found"
    print(f"{action} stale colliding Streamlit page files:")
    for slug, stale_path, tracked_path in stale_collisions:
        print(f"  - {stale_path} conflicts with tracked page {tracked_path} via pathname '{slug}'")
        if args.apply:
            (repo_dir / stale_path).unlink(missing_ok=True)

    if args.apply:
        print("Stale colliding page files removed.")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())