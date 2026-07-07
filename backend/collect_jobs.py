#!/usr/bin/env python3
"""CLI entry point for the Job Collection Runner.

Usage:
    python collect_jobs.py --source greenhouse --max-pages 3 --verbose
    python collect_jobs.py --dry-run --source greenhouse
    python collect_jobs.py --company Acme --max-pages 5
    python collect_jobs.py --list-sources
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any, Optional

from app.collectors.models import CollectorQuery


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run job collection from registered sources.",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Specific collector source to run (e.g., 'greenhouse'). "
        "If omitted, all registered collectors run.",
    )
    parser.add_argument(
        "--company",
        type=str,
        default=None,
        help="Company filter passed as additional_filters['company_name'] "
        "to the collector.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Override max_pages_per_source for all collectors.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run all lifecycle steps except save(). Prints what would "
        "be saved without persisting.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable detailed per-stage logging output.",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        default=False,
        help="List all registered collector sources and exit.",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        nargs="*",
        default=None,
        help="Search keywords (e.g., 'Python FastAPI').",
    )
    parser.add_argument(
        "--locations",
        type=str,
        nargs="*",
        default=None,
        help="Location filters (e.g., 'Remote' 'New York').",
    )
    parser.add_argument(
        "--remote-only",
        action="store_true",
        default=False,
        help="Only collect remote positions.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Maximum number of jobs to collect per source (default: 50).",
    )
    return parser.parse_args(argv)


def _print(
    message: str,
    verbose: bool = False,
    force: bool = False,
) -> None:
    if force or verbose:
        print(message)


def _get_collectors(source_name: Optional[str] = None) -> list[tuple[str, Any]]:
    from app.collectors.registry import CollectorRegistry

    CollectorRegistry.discover("app.collectors.plugins")
    all_collectors = CollectorRegistry.list_collectors()

    if source_name:
        normalized = source_name.lower()
        if normalized not in all_collectors:
            print(
                f"Error: source '{source_name}' not found. "
                f"Available sources: {', '.join(all_collectors)}",
                file=sys.stderr,
            )
            sys.exit(1)
        return [(normalized, CollectorRegistry.get(normalized))]

    return [(name, CollectorRegistry.get(name)) for name in all_collectors]


def _get_config(source_name: str) -> dict[str, Any]:
    from app.collectors.config import CollectorConfigProvider

    return CollectorConfigProvider.get_source_config(source_name)


async def _run_collector(
    collector_cls: type,
    source_name: str,
    config: dict[str, Any],
    query: CollectorQuery,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    collector = collector_cls(config, logger=None)
    result: dict[str, Any] = {
        "source": source_name,
        "success": False,
        "collected": 0,
        "saved": 0,
        "duplicates": 0,
        "errors": [],
        "duration": 0.0,
    }

    start = time.monotonic()
    try:
        _print(f"  [{source_name}] Initializing...", verbose)
        await collector.initialize()

        _print(f"  [{source_name}] Collecting...", verbose)
        raw_result = await collector.collect(query)
        discovered = raw_result.stats.total_discovered
        result["collected"] = discovered
        _print(
            f"  [{source_name}] Discovered {discovered} jobs.",
            verbose,
        )

        if not raw_result.success and raw_result.errors:
            for err in raw_result.errors:
                result["errors"].append(
                    f"{err.error_type}: {err.error_message}"
                )
            _print(
                f"  [{source_name}] Collection had errors, "
                f"attempting to normalize partial data.",
                verbose,
            )

        _print(f"  [{source_name}] Normalizing...", verbose)
        normalized = await collector.normalize(raw_result.raw_data)
        _print(
            f"  [{source_name}] Normalized {len(normalized)} jobs.",
            verbose,
        )

        _print(f"  [{source_name}] Validating...", verbose)
        validated = await collector.validate(normalized)
        _print(
            f"  [{source_name}] {len(validated)} valid, "
            f"{len(normalized) - len(validated)} invalid.",
            verbose,
        )

        _print(f"  [{source_name}] Deduplicating...", verbose)
        deduped = await collector.deduplicate(
            validated,
            raw_result.existing_source_ids,
        )
        duplicates = len(validated) - len(deduped)
        result["duplicates"] = duplicates
        _print(
            f"  [{source_name}] {duplicates} duplicates skipped, "
            f"{len(deduped)} new jobs.",
            verbose,
        )

        if dry_run:
            _print(
                f"  [{source_name}] DRY RUN: would save "
                f"{len(deduped)} job(s).",
                force=True,
            )
            result["saved"] = 0
            result["success"] = True
        else:
            _print(f"  [{source_name}] Saving {len(deduped)} job(s)...", verbose)
            save_result = await collector.save(deduped)
            result["saved"] = save_result.stats.total_saved
            for err in save_result.errors:
                result["errors"].append(
                    f"{err.error_type}: {err.error_message}"
                )
            result["success"] = save_result.success

    except Exception as e:
        result["errors"].append(f"{type(e).__name__}: {e}")
        result["success"] = False
    finally:
        _print(f"  [{source_name}] Cleaning up...", verbose)
        await collector.cleanup()
        result["duration"] = time.monotonic() - start

    return result


def _print_summary(results: list[dict[str, Any]]) -> None:
    total_collected = sum(r["collected"] for r in results)
    total_saved = sum(r["saved"] for r in results)
    total_duplicates = sum(r["duplicates"] for r in results)
    total_errors = sum(len(r["errors"]) for r in results)
    total_duration = sum(r["duration"] for r in results)
    all_success = all(r["success"] for r in results)
    any_errors = any(r["errors"] for r in results)

    print()
    print("=" * 50)
    print("COLLECTION SUMMARY")
    print("=" * 50)

    for r in results:
        status = "OK" if r["success"] else "FAIL"
        print(f"  {r['source']}: {status} "
              f"({r['collected']} collected, "
              f"{r['saved']} saved, "
              f"{r['duplicates']} skipped, "
              f"{len(r['errors'])} errors, "
              f"{r['duration']:.2f}s)")

    print("-" * 50)
    print(f"  Total collected:  {total_collected}")
    print(f"  Total saved:      {total_saved}")
    print(f"  Duplicates:       {total_duplicates}")
    print(f"  Total errors:     {total_errors}")
    print(f"  Total time:       {total_duration:.2f}s")
    print(f"  Overall status:   {'SUCCESS' if all_success and not any_errors else 'FAILURE'}")

    if any_errors:
        print()
        print("ERRORS:")
        for r in results:
            if r["errors"]:
                print(f"  {r['source']}:")
                for err in r["errors"]:
                    print(f"    - {err}")


async def _run(args: argparse.Namespace) -> int:
    if args.list_sources:
        from app.collectors.registry import CollectorRegistry

        CollectorRegistry.discover("app.collectors.plugins")
        sources = CollectorRegistry.list_collectors()
        if sources:
            print("Registered collector sources:")
            for name in sources:
                print(f"  - {name}")
        else:
            print("No collector sources registered.")
        return 0

    collectors = _get_collectors(args.source)
    if not collectors:
        print("No collectors found to run.", file=sys.stderr)
        return 1

    additional_filters: dict[str, Any] = {}
    if args.company:
        additional_filters["company_name"] = args.company

    query = CollectorQuery(
        keywords=args.keywords or [],
        locations=args.locations or [],
        remote_only=args.remote_only,
        max_results=args.max_results,
        additional_filters=additional_filters,
    )

    print(f"Running {len(collectors)} collector(s)...")
    if args.dry_run:
        print("DRY RUN MODE: jobs will not be saved.")
    if args.verbose:
        print("Verbose mode enabled.")
    if args.company:
        print(f"Company filter: {args.company}")
    if args.keywords:
        print(f"Keywords: {args.keywords}")
    if args.locations:
        print(f"Locations: {args.locations}")
    print()

    results: list[dict[str, Any]] = []
    for source_name, collector_cls in collectors:
        if collector_cls is None:
            print(f"  [{source_name}] Skipping (no class found).")
            continue

        config = _get_config(source_name)
        if args.max_pages is not None:
            config["max_pages_per_source"] = args.max_pages

        _print(f"[{source_name}] Starting collection...", verbose=True)
        result = await _run_collector(
            collector_cls,
            source_name,
            config,
            query,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        results.append(result)

    _print_summary(results)
    return 0 if all(r["success"] for r in results) else 1


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    import asyncio

    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 1
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
