from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from collect_jobs import _parse_args, _run, _run_collector, main


class TestParseArgs:
    def test_defaults(self):
        args = _parse_args([])
        assert args.source is None
        assert args.company is None
        assert args.max_pages is None
        assert args.dry_run is False
        assert args.verbose is False
        assert args.list_sources is False
        assert args.keywords is None
        assert args.locations is None
        assert args.remote_only is False
        assert args.max_results == 50

    def test_source(self):
        args = _parse_args(["--source", "greenhouse"])
        assert args.source == "greenhouse"

    def test_dry_run(self):
        args = _parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_verbose(self):
        args = _parse_args(["--verbose"])
        assert args.verbose is True

    def test_company(self):
        args = _parse_args(["--company", "Acme"])
        assert args.company == "Acme"

    def test_max_pages(self):
        args = _parse_args(["--max-pages", "5"])
        assert args.max_pages == 5

    def test_list_sources(self):
        args = _parse_args(["--list-sources"])
        assert args.list_sources is True

    def test_keywords(self):
        args = _parse_args(["--keywords", "Python", "FastAPI"])
        assert args.keywords == ["Python", "FastAPI"]

    def test_locations(self):
        args = _parse_args(["--locations", "Remote"])
        assert args.locations == ["Remote"]

    def test_remote_only(self):
        args = _parse_args(["--remote-only"])
        assert args.remote_only is True

    def test_max_results(self):
        args = _parse_args(["--max-results", "100"])
        assert args.max_results == 100


class TestMain:
    def test_unknown_source_exits(self):
        with pytest.raises(SystemExit) as exc:
            main(["--source", "nonexistent"])
        assert exc.value.code == 1

    @patch("collect_jobs._run")
    def test_keyboard_interrupt(self, mock_run: MagicMock):
        mock_run.side_effect = KeyboardInterrupt

        with patch("collect_jobs._get_collectors") as mock_get:
            mock_get.return_value = [("greenhouse", MagicMock())]
            exit_code = main(["--source", "greenhouse"])

        assert exit_code == 1

    @patch("collect_jobs._run")
    def test_fatal_exception(self, mock_run: MagicMock):
        mock_run.side_effect = RuntimeError("boom")

        with patch("collect_jobs._get_collectors") as mock_get:
            mock_get.return_value = [("greenhouse", MagicMock())]
            exit_code = main(["--source", "greenhouse"])

        assert exit_code == 1


class TestRunCollector:
    """Test _run_collector directly — passes mock objects, no patching needed."""

    @pytest.fixture
    def mock_collector_instance(self):
        inst = MagicMock()
        inst.initialize = AsyncMock()
        inst.cleanup = AsyncMock()
        return inst

    @pytest.fixture
    def mock_collect_cls(self, mock_collector_instance):
        cls = MagicMock()
        cls.return_value = mock_collector_instance
        return cls

    def _success_collect_result(self, count=10):
        r = MagicMock()
        r.success = True
        r.stats.total_discovered = count
        r.raw_data = [{"id": i} for i in range(count)]
        r.errors = []
        r.existing_source_ids = set()
        return r

    def _success_save_result(self, count=1):
        r = MagicMock()
        r.success = True
        r.stats.total_saved = count
        r.errors = []
        return r

    @pytest.mark.asyncio
    async def test_successful_run(self, mock_collect_cls, mock_collector_instance):
        mock_collector_instance.collect = AsyncMock(
            return_value=self._success_collect_result(10),
        )
        mock_job = MagicMock()
        mock_collector_instance.normalize = AsyncMock(return_value=[mock_job])
        mock_collector_instance.validate = AsyncMock(return_value=[mock_job])
        mock_collector_instance.deduplicate = AsyncMock(return_value=[mock_job])
        mock_collector_instance.save = AsyncMock(
            return_value=self._success_save_result(1),
        )

        result = await _run_collector(
            mock_collect_cls,
            "greenhouse",
            {},
            MagicMock(),
            dry_run=False,
            verbose=False,
        )

        assert result["success"] is True
        assert result["source"] == "greenhouse"
        assert result["collected"] == 10
        assert result["saved"] == 1
        assert result["errors"] == []
        mock_collector_instance.initialize.assert_awaited_once()
        mock_collector_instance.collect.assert_awaited_once()
        mock_collector_instance.normalize.assert_awaited_once()
        mock_collector_instance.validate.assert_awaited_once()
        mock_collector_instance.deduplicate.assert_awaited_once()
        mock_collector_instance.save.assert_awaited_once()
        mock_collector_instance.cleanup.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dry_run_skips_save(self, mock_collect_cls, mock_collector_instance):
        mock_collector_instance.collect = AsyncMock(
            return_value=self._success_collect_result(5),
        )
        mock_job = MagicMock()
        mock_collector_instance.normalize = AsyncMock(return_value=[mock_job])
        mock_collector_instance.validate = AsyncMock(return_value=[mock_job])
        mock_collector_instance.deduplicate = AsyncMock(return_value=[mock_job])
        mock_collector_instance.save = AsyncMock()

        result = await _run_collector(
            mock_collect_cls,
            "greenhouse",
            {},
            MagicMock(),
            dry_run=True,
            verbose=False,
        )

        assert result["success"] is True
        assert result["saved"] == 0
        mock_collector_instance.initialize.assert_awaited_once()
        mock_collector_instance.collect.assert_awaited_once()
        mock_collector_instance.normalize.assert_awaited_once()
        mock_collector_instance.validate.assert_awaited_once()
        mock_collector_instance.deduplicate.assert_awaited_once()
        mock_collector_instance.save.assert_not_called()
        mock_collector_instance.cleanup.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_collector_exception(self, mock_collect_cls, mock_collector_instance):
        mock_collector_instance.initialize = AsyncMock()
        mock_collector_instance.collect = AsyncMock(side_effect=ValueError("bad data"))
        mock_collector_instance.cleanup = AsyncMock()

        result = await _run_collector(
            mock_collect_cls,
            "greenhouse",
            {},
            MagicMock(),
            dry_run=False,
            verbose=False,
        )

        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert "ValueError" in result["errors"][0]
        mock_collector_instance.initialize.assert_awaited_once()
        mock_collector_instance.collect.assert_awaited_once()
        mock_collector_instance.cleanup.assert_awaited_once()


class TestRun:
    """Test _run with mocked _get_collectors and _get_config."""

    @pytest.fixture
    def mock_collector_instance(self):
        inst = MagicMock()
        inst.name = "greenhouse"
        return inst

    def _make_collect_cls(self, instance):
        cls = MagicMock()
        cls.return_value = instance
        return cls

    @patch("collect_jobs._get_config")
    @patch("collect_jobs._get_collectors")
    @pytest.mark.asyncio
    async def test_success(
        self,
        mock_get_collectors: MagicMock,
        mock_get_config: MagicMock,
        mock_collector_instance: MagicMock,
    ):
        cls = self._make_collect_cls(mock_collector_instance)
        mock_get_collectors.return_value = [("greenhouse", cls)]
        mock_get_config.return_value = {}

        mock_collector_instance.initialize = AsyncMock()
        mc = MagicMock()
        mc.success = True
        mc.stats.total_discovered = 3
        mc.raw_data = [{"id": 1}]
        mc.errors = []
        mc.existing_source_ids = set()
        mock_collector_instance.collect = AsyncMock(return_value=mc)
        mock_job = MagicMock()
        mock_collector_instance.normalize = AsyncMock(return_value=[mock_job])
        mock_collector_instance.validate = AsyncMock(return_value=[mock_job])
        mock_collector_instance.deduplicate = AsyncMock(return_value=[mock_job])
        ms = MagicMock()
        ms.success = True
        ms.stats.total_saved = 1
        ms.errors = []
        mock_collector_instance.save = AsyncMock(return_value=ms)
        mock_collector_instance.cleanup = AsyncMock()

        args = _parse_args(["--source", "greenhouse"])
        exit_code = await _run(args)
        assert exit_code == 0

    @patch("collect_jobs._get_config")
    @patch("collect_jobs._get_collectors")
    @pytest.mark.asyncio
    async def test_failure(
        self,
        mock_get_collectors: MagicMock,
        mock_get_config: MagicMock,
        mock_collector_instance: MagicMock,
    ):
        cls = self._make_collect_cls(mock_collector_instance)
        mock_get_collectors.return_value = [("greenhouse", cls)]
        mock_get_config.return_value = {}

        mock_collector_instance.initialize = AsyncMock()
        mock_collector_instance.collect = AsyncMock(side_effect=ValueError("fail"))
        mock_collector_instance.cleanup = AsyncMock()

        args = _parse_args(["--source", "greenhouse"])
        exit_code = await _run(args)
        assert exit_code == 1

    @patch("collect_jobs._get_config")
    @patch("collect_jobs._get_collectors")
    @pytest.mark.asyncio
    async def test_multiple_collectors(
        self,
        mock_get_collectors: MagicMock,
        mock_get_config: MagicMock,
    ):
        def _make_inst(name: str):
            inst = MagicMock()
            inst.initialize = AsyncMock()
            mc = MagicMock()
            mc.success = True
            mc.stats.total_discovered = 2
            mc.raw_data = [{"id": 1}]
            mc.errors = []
            mc.existing_source_ids = set()
            inst.collect = AsyncMock(return_value=mc)

            mock_job = MagicMock()
            inst.normalize = AsyncMock(return_value=[mock_job])
            inst.validate = AsyncMock(return_value=[mock_job])
            inst.deduplicate = AsyncMock(return_value=[mock_job])
            ms = MagicMock()
            ms.success = True
            ms.stats.total_saved = 1
            ms.errors = []
            inst.save = AsyncMock(return_value=ms)
            inst.cleanup = AsyncMock()
            return inst

        inst1 = _make_inst("greenhouse")
        inst2 = _make_inst("lever")

        cls1 = MagicMock()
        cls1.return_value = inst1
        cls2 = MagicMock()
        cls2.return_value = inst2

        mock_get_collectors.return_value = [("greenhouse", cls1), ("lever", cls2)]
        mock_get_config.return_value = {}

        args = _parse_args([])
        exit_code = await _run(args)
        assert exit_code == 0

        inst1.initialize.assert_awaited_once()
        inst2.initialize.assert_awaited_once()
        inst1.save.assert_awaited_once()
        inst2.save.assert_awaited_once()

    @patch("collect_jobs._get_config")
    @patch("collect_jobs._get_collectors")
    @pytest.mark.asyncio
    async def test_max_pages_override(
        self,
        mock_get_collectors: MagicMock,
        mock_get_config: MagicMock,
        mock_collector_instance: MagicMock,
    ):
        cls = self._make_collect_cls(mock_collector_instance)
        mock_get_collectors.return_value = [("greenhouse", cls)]
        config: dict[str, Any] = {"max_pages_per_source": 3}
        mock_get_config.return_value = config

        mock_collector_instance.initialize = AsyncMock()
        mc = MagicMock()
        mc.success = True
        mc.stats.total_discovered = 0
        mc.raw_data = []
        mc.errors = []
        mc.existing_source_ids = set()
        mock_collector_instance.collect = AsyncMock(return_value=mc)
        mock_collector_instance.normalize = AsyncMock(return_value=[])
        mock_collector_instance.validate = AsyncMock(return_value=[])
        mock_collector_instance.deduplicate = AsyncMock(return_value=[])
        ms = MagicMock()
        ms.success = True
        ms.stats.total_saved = 0
        ms.errors = []
        mock_collector_instance.save = AsyncMock(return_value=ms)
        mock_collector_instance.cleanup = AsyncMock()

        args = _parse_args(["--source", "greenhouse", "--max-pages", "10"])
        exit_code = await _run(args)
        assert exit_code == 0
        assert config["max_pages_per_source"] == 10

    @patch("app.collectors.registry.CollectorRegistry")
    @pytest.mark.asyncio
    async def test_list_sources(self, MockRegistry: MagicMock):
        MockRegistry.discover = MagicMock()
        MockRegistry.list_collectors.return_value = ["greenhouse", "lever"]

        args = _parse_args(["--list-sources"])
        exit_code = await _run(args)
        assert exit_code == 0
