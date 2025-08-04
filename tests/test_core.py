import os
import builtins
import types

import pytest

import botautomatic as ba


def test_parse_duration_basic():
    assert ba.parse_duration("2h") == 7200
    assert ba.parse_duration("1d2h3m4s") == 1 * 86400 + 2 * 3600 + 3 * 60 + 4
    # пустая строка — дефолт
    assert ba.parse_duration("") == ba.wait_time


def test_parse_new_format_minimal_random(monkeypatch):
    # Подмена сборки текста, чтобы не зависеть от файлов
    monkeypatch.setattr(ba, "build_text", lambda *args, **kwargs: "BUILT")
    gid, text, img, delay = ba.parse("156716828:[-:-:-:-:-:-:-:457239113]|12h")
    assert gid == 156716828
    assert text == "BUILT"
    assert img == 457239113
    assert delay == 12 * 3600


def test_parse_new_format_with_named_variant(monkeypatch):
    monkeypatch.setattr(ba, "build_text", lambda *args, **kwargs: "BUILT_NAMED")
    gid, text, img, delay = ba.parse("42:[###name:1:2:3:4:5:###link:123]|45m")
    assert gid == 42
    assert text == "BUILT_NAMED"
    assert img == 123
    assert delay == 45 * 60


def test_parse_old_format_no_seconds(tmp_path, monkeypatch):
    # Создадим временный файл с содержимым текста
    text_path = tmp_path / "x.txt"
    text_path.write_text("HELLO", encoding="utf-8")
    s = f"100:{text_path.as_posix()}|999"
    gid, path_or_text, image, delay = ba.parse(s)
    # prepare должен распознать строку как путь и загрузить
    txt, _ = ba.prepare(path_or_text)
    assert gid == 100
    assert image == 999
    assert delay is None
    assert txt == "HELLO"


def test_parse_old_format_with_seconds(tmp_path):
    text_path = tmp_path / "y.txt"
    text_path.write_text("TEXT", encoding="utf-8")
    s = f"77:{text_path.as_posix()}|111?3600"
    gid, path_or_text, image, delay = ba.parse(s)
    assert gid == 77
    assert image == 111
    assert delay == 3600
    # prepare загрузит контент
    txt, _ = ba.prepare(path_or_text)
    assert txt == "TEXT"


def test_build_text_random_variants(monkeypatch):
    # Заменим загрузчики, чтобы вернуть контролируемые варианты
    def fake_load(path):
        if path.endswith("tags.txt"):
            return [("1", "#t1"), ("2", "#t2")]
        if path.endswith("block1.txt"):
            return [("intro", "B1")]
        if path.endswith("block2.txt"):
            return [("1", "B2-1"), ("2", "B2-2")]
        if path.endswith("block3.txt"):
            return [("1", "B3-1")]
        if path.endswith("block4.txt"):
            return [("x", "B4-x")]
        if path.endswith("block5.txt"):
            return [("final", "B5-final")]
        if path.endswith("links.txt"):
            return [("cta", "LINK")]
        return []
    monkeypatch.setattr(ba, "load_variants_file", fake_load)

    # Все '-' => случайный, но в нашем наборе фактически по одному элементу на блок => детерминированно
    txt = ba.build_text("-", "-", "-", "-", "-", "-", "-")
    assert "#t" in txt and "B1" in txt and "B2-" in txt and "B3-1" in txt and "B4-x" in txt and "B5-final" in txt and "LINK" in txt


def test_build_text_specific_variants(monkeypatch):
    def fake_load(path):
        if path.endswith("tags.txt"):
            return [("lite", "#lite"), ("bobi", "#bobi")]
        if path.endswith("block1.txt"):
            return [("1", "B1-1"), ("2", "B1-2")]
        if path.endswith("block2.txt"):
            return [("2", "B2-2")]
        if path.endswith("block3.txt"):
            return [("###tajikistan".lstrip("#"), "TJ")]
        if path.endswith("block4.txt"):
            return [("1", "B4-1")]
        if path.endswith("block5.txt"):
            return [("closing", "B5-C")]
        if path.endswith("links.txt"):
            return [("1", "L1")]
        return []
    monkeypatch.setattr(ba, "load_variants_file", fake_load)

    txt = ba.build_text("lite", "2", "2", "###tajikistan", "1", "closing", "1")
    assert "#lite" in txt and "B1-2" in txt and "B2-2" in txt and "TJ" in txt and "B4-1" in txt and "B5-C" in txt and "L1" in txt


def test_prepare_text_pass_through():
    # если это уже текст (есть перенос или нет .txt) — вернуть как есть
    text = "LINE1\nLINE2"
    got, tdict = ba.prepare(text)
    assert got == text
    assert isinstance(tdict, dict)


def test_prepare_text_from_file(tmp_path, monkeypatch):
    p = tmp_path / "z.txt"
    p.write_text("CONTENT", encoding="utf-8")
    got, _ = ba.prepare(p.as_posix())
    assert got == "CONTENT"