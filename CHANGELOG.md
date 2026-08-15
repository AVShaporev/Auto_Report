# Changelog

Все значимые изменения Auto_Report (backend). Формат по
[Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версионирование [SemVer](https://semver.org/lang/ru/) — bump на каждый
фикс/фичу; см. правило в feedback_autoreport_versioning.md.

## [1.0.0] — 2026-08-16

Первая версия с формальным версионированием. Проект давно в prod у hi-tech,
за это время проделаны все этапы: базовый CRUD, SaaS multi-tenant,
Mobile M1-M6, docker+CI/CD, канон spec_order_statuses и др.

### Added
- `VERSION` файл в корне репо.
- `main.py` логгирует `📦 Auto_Report v{ver} starting…` при старте.
