# КПО ДЗ №3 — Антиплагиат

Проект реализует приложение для проверки текстового файла на антиплагиат.

Задание выполнено в рамках курса "Конструирование программного обеспечения". 

Реализованы:
- приём работ студентов;
- хранение файлов;
- анализ на плагиат; 
- выдача отчётов;
- API Gateway как единая точка входа.

## Архитектура

### Сервисы

1) API Gateway (`gateway`, порт 8000)  
   - Принимает запросы клиентов.
   - Фиксирует сдачу работы (кто/когда/по какому заданию) в своей БД.
   - Оркестрирует синхронные вызовы:
     - сохраняет файл через File Storing Service;
     - запускает анализ через File Analysis Service.
   - Отдаёт агрегированные ответы (work + report).

2) File Storing Service (`file-service`, порт 8001)  
   - Хранит файлы на диске (в Docker volume).
   - Хранит метаданные о файлах (имя, размер, sha256, путь) в SQLite.
   - Умеет выдавать файл и метаданные.

3) File Analysis Service (`analysis-service`, порт 8002)  
   - Хранит результаты анализа (отчёты) в SQLite + JSON-файл отчёта на диске.
   - Самостоятельно получает нужный файл из File Storing Service по `file_id`.
   - Отдаёт отчёты и аналитику по работе.

### Хранилища
- Каждый сервис имеет свою SQLite БД.
- Файлы и отчёты лежат в volume (сохраняются между перезапусками).

### Сценарий использования
1) Клиент вызывает gateway с файлом, `student_id`, `assignment_id`.  
2) Gateway:
   - создаёт запись Work (status=`CREATED`),
   - вызывает File Service и получает `file_id`, `sha256`,
   - обновляет Work (status=`FILE_STORED`),
   - вызывает Analysis Service (work_id + метаданные),
   - обновляет Work (status=`ANALYZED` либо `ANALYSIS_FAILED`).
3) Клиент получает JSON с Work + Report.

### Обработка ошибок микросервисов
- Если File Service недоступен: gateway сохраняет Work со статусом `FILE_STORE_FAILED` и возвращает HTTP 503.
- Если Analysis Service недоступен: файл уже сохранён, gateway ставит `ANALYSIS_FAILED` и возвращает HTTP 503; можно повторить анализ `retry-analysis`.

### Структура проекта

```
├── docker-compose.yml                - конфигурация docker-compose
├── postman_collection.json           - коллекция запросов для Postman
├── README.md                         
├── scripts
│   └── smoke_test.sh                 - скрипт быстрой проверки  
└── services
    ├── analysis_service              
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── src                        
    │       └── analysis_service
    │           ├── analyzer.py       - логика анализа текста
    │           ├── clients.py        - http клиент для взаимодействия с File Storing Service
    │           ├── config.py         - конфигурация сервиса (порты, пути к данным)
    │           ├── db.py             - подключение к БД 
    │           ├── __init__.py       
    │           ├── main.py           - точка входа FastAPI
    │           ├── models.py         - модели базы данных сервиса
    │           └── schemas.py        - Pydantic-схемы для валидации входных данных
    ├── file_service
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── src
    │       └── file_service
    │           ├── config.py         - конфигурация сервиса
    │           ├── db.py             - настройка БД
    │           ├── __init__.py       
    │           ├── main.py           - FastAPI приложение сервиса
    │           ├── models.py         - модель файла и метаданных
    │           ├── schemas.py        - Pydantic-схемы для API сервиса
    │           └── storage.py        - логика сохранения файлов на диск и вычисления sha256
    └── gateway
        ├── Dockerfile
        ├── requirements.txt
        └── src
            └── gateway
                ├── clients.py        - http клиенты для синхронного взаимодействия
                ├── config.py         - конфигурация API
                ├── db.py             - настройка БД
                ├── __init__.py
                ├── main.py           - точка входа FastAPI
                ├── models.py         - модель полученной работы в Gateway
                └── schemas.py        - Pydantic-схемы входных данных и ответов Gateway
```

## Алгоритм определения плагиата

Использована наивная реализация: плагиат есть, если существует более ранняя сдача другим студентом той же работы.

В реализации:
- File Service вычисляет `sha256` загруженного файла.
- Analysis Service считает, что две работы одинаковы, если совпадает `sha256`.
- Плагиат - существует Work с тем же `file_sha256` и `submitted_at` меньше текущего, при этом `student_id` отличается.
- В отчёте фиксируется автор оригинальной работы (`work_id` и `student_id` первой найденной более ранней сдачи).

## Облако слов
Analysis Service умеет строить облако слов, проксируя запрос к quickchart.io Word Cloud API и возвращает PNG.

## Запуск

Развернуть докер:

```bash
docker compose up --build
```

После старта:
- Gateway Swagger: http://localhost:8000/docs  
- File Service Swagger: http://localhost:8001/docs  
- Analysis Service Swagger: http://localhost:8002/docs  

Отправка работы:

```bash
curl -F "student_id=<student_id>" -F "assignment_id=<assignment_id>" -F "file=@file_path" http://localhost:8000/works
```

Получить отчёты по работе:

```bash
curl http://localhost:8000/works/<work_id>/reports
```

Повторить анализ, если Analysis Service был недоступен:

```bash
curl -X POST http://localhost:8000/works/<work_id>/retry-analysis
```

Построить облаков слов:

```bash
curl http://localhost:8002/reports/<report_id>/wordcloud --output <png_path>
```

В `scripts/smoke_test.sh` есть пример автоматической проверки:

```bash
bash scripts/smoke_test.sh
```

## Запуск через Postman

После развертывания докера, добавить файл `postman_collection.json` в Postman и выполнить запросы.
