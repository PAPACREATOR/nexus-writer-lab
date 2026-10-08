"""Repeat the unchanged real-route assertions 100 times per process across shards."""
import os
import pytest
from nexus.tests.test_native_writer_route_real import (
    test_installed_writer_is_confined_and_returns_only_a_human_approved_candidate as real_route,
)

@pytest.mark.parametrize('process', ['book', 'convert_pdf'])
@pytest.mark.parametrize('index', range(25))
def test_real_route_repetition(tmp_path, monkeypatch, process, index):
    shard=int(os.environ['LAB_SHARD'])
    name=f'Folha Lisboa ação espaço {shard * 25 + index}'
    work=tmp_path/name
    if index == 24:
        work=work/('caminho longo ' * 8)/('mais longo ' * 8)
    work.mkdir(parents=True)
    real_route(work, monkeypatch, process)
