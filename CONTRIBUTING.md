# Работа с репозиторием

## Ветки и pull request

Для сдачи ЛР1 создавайте ветку по шаблону `lab1-[role]-initiation`, где `[role]`
— `product`, `ai-engineer`, `delivery` или `quality-safety`. Название PR:
`Lab1: [Role] — Initiation Deliverables`. Каждый PR должен содержать артефакты
своей роли и проходить CI.

PR-шаблон находится в `.github/pull_request_template.md`. Не включайте в коммиты
`.env`, API-ключи, приватные данные интервью и реальные пользовательские данные.
Workflow запускает проверки на PR, но сам по себе не запрещает слияние при
ошибке. Владелец репозитория должен включить branch protection для `main` и
добавить CI job `verify` как обязательную проверку.

## Локальная разработка

Скопируйте `.env.example` в `.env`, затем выполните:

```sh
docker compose -f compose.dev.yml up --build
```

Проверки без Docker:

```sh
python -m pip install -r requirements.txt
ruff check .
ruff format --check .
pytest
```

Форматирование:

```sh
ruff format .
```

Не передавайте текст задач или содержимое репозитория внешней модели, пока команда
не согласовала провайдера, разрешённый контекст и правила работы с данными.