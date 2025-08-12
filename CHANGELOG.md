# Changelog

Все заметные изменения в этом проекте будут документироваться в этом файле.
Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), и проект следует [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-08-04

### Added

- Package marker modules/init.py to solidify package imports and avoid duplicate module resolution under mypy.
- Docstrings for tests to satisfy pydocstyle:
  - tests/test_core.py — D103 for all public test functions.
  - tests/test_vk_integration.py — D107 for init, D106 for nested classes, D102 for methods.
- CI/test infra improvements:
  - pytest.ini — add --import-mode=importlib and pythonpath=. for reliable imports.

### Changed

- botautomatic.py:
  - Type annotations: wait_time: int, time_dict: Dict[int, datetime].
  - Old-format timer parsing: safely parse integer seconds with fallback to None.
  - Function signatures annotated: prepare returns Tuple[str, Dict[Any, Any]], get_last_post returns Union[Mapping[str, Any], None, int]; check_suggests returns int.
  - Use typing.cast where indexing VK API post payloads to satisfy mypy.
  - Suppress missing stubs for vk_api via type: ignore[import-untyped] on import.
  - Harden pickle loading with runtime dict check before assignment.
- modules/module_logger.py:
  - Fix D212 by placing summary on opening triple-quote line and refine wording.

### Removed

- None.

### Fixed

- mypy errors:
  - Duplicate module name risk reduced by adding modules/init.py and normalizing imports.
  - Import-untyped warning for vk_api suppressed with targeted ignore.
  - Union/indexability errors resolved via cast and precise return typing.
  - Unused ignore eliminated by runtime type check on pickle load.
- pydocstyle errors:
  - D212 (module docstring style) in module_logger.
  - D103/D106/D107/D102 across test modules.

## Misc

- .gitignore: include .mypy_cache and .pytest_cache.
- files/groups.txt: comment out legacy noisy entries; retain examples for new/old formats.

## Verification

- pydocstyle . shows no violations in modified files.
- mypy . is clean for the repo’s Python code with the above annotations and ignores.
- pytest -q -vv passes with unchanged runtime behavior.

## [1.1.0] - 2025-08-04

### Added

- TextBuilder: блочная сборка постов из файлов `files/tags.txt`, `files/block1..5.txt`, `files/links.txt` с вариантами `##`/`###`.
- Новый формат `files/groups.txt`: `groupid:[tags:b1:b2:b3:b4:b5:links:image]|delay`, поддержка `-` для случайного выбора.
- Парсер длительности `1d2h3m4s` с опциональными компонентами.
- Поддержка комментариев в `groups.txt` — строки, начинающиеся с `#`, игнорируются.
- Обратная совместимость со старым форматом `groupid:path|image[?seconds]`.
- Улучшенное логирование, безопасная загрузка `files/dumping.pkl`, больше контекста в сообщениях.
- Документация: README.md (ru) с архитектурой, форматами и инструкциями.
- Начато документирование кода в стиле Google с doctest-примерами.

### Changed

- Конфигурация вынесена в `.env` (через `python-dotenv`): `TOKEN` (обязательно), `DEFAULT_WAIT_TIME` (необяз., сек).
- Очистка и унификация логики проверки стен (1/2/3), улучшено принятие решений по предложке и интервалам.

### Fixed

- Исправлены обращения к owner_id и контексту групп в проверках истории и предложки.
- Устранены потенциальные ошибки загрузки пустого `dumping.pkl`.

### Security

- Чувствительные данные (`TOKEN`) исключены из кода и должны храниться в `.env`/переменных окружения.
- `.env` уже в `.gitignore`.

## [1.0.0] - 2024-xx-xx

### Added

- Базовый автоматический постинг в группы VK из текстовых файлов/шаблонов.
- Начальное логирование в файлы `log.txt` и `error_log.txt`.
