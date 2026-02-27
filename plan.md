# План развития string-gen

## Текущее состояние

Библиотека генерирует случайные строки по регулярным выражениям. Поддерживает основные конструкции regex (литералы, классы символов, квантификаторы, группы, альтернации, backreferences, lookahead). Чистый Python, без зависимостей, 100% test coverage, Python 3.8–3.14, CPython + PyPy.

## Анализ конкурентов

| Библиотека | Stars | Уникальные фичи |
|------------|-------|------------------|
| [rstr](https://github.com/leapfrogonline/rstr) | ~100 | Convenience-методы (`letters()`, `digits()`, `urlsafe()`…), `include`/`exclude` символов, кастомные алфавиты |
| [exrex](https://github.com/asciimoo/exrex) | ~550 | Перечисление **всех** совпадений, подсчёт количества, упрощение regex, CLI, Unicode, генераторы |
| [hypothesis from_regex](https://hypothesis.readthedocs.io/) | — | Полный Unicode, параметр `alphabet`, интеграция с property-based testing |

---

## Фичи и улучшения

### 1. Итератор / генератор (приоритет: высокий) ✅ реализовано

**Проблема:** Для генерации N строк нужно вручную вызывать `render()` в цикле или использовать `render_list()`, который сразу создаёт весь список в памяти.

**Решение:** Добавить протокол итератора и метод-генератор.

```python
gen = StringGen(r"\d{4}")

# Бесконечный итератор
for value in gen:
    print(value)
    break

# Ленивый генератор с лимитом
for value in gen.stream(100):
    process(value)

# Совместимость с itertools
from itertools import islice
values = list(islice(gen, 10))
```

**Реализация:**
- `__iter__` — бесконечный итератор, каждый `__next__` вызывает `render()`
- `stream(count)` — генератор, yield'ит `count` строк лениво

---

### 2. Кастомные алфавиты / charset (приоритет: требует проработки) ✅ реализовано

**Проблема:** Генерация основана на `string.printable` (100 ASCII-символов). `\w`, `\d`, `.` генерируют только ASCII. Простой флаг `unicode=True` слишком размыт — непонятно, какие именно символы будут генерироваться: весь Unicode (1.1M+ code points) — это хаос.

**Реальная потребность:** Генерировать строки на конкретном языке/алфавите — русский, китайский, арабский и т.д. Или смешанный набор символов для i18n-тестирования.

**Варианты решения:**

#### Вариант A: Параметр `alphabet` с предустановками

```python
from string_gen import StringGen
from string_gen.alphabets import CYRILLIC, CJK, LATIN_EXTENDED

# Генерация на кириллице
gen = StringGen(r"\w{10}", alphabet=CYRILLIC)
gen.render()  # "щПрвБТлоМк"

# Смешанный набор
gen = StringGen(r"\w{10}", alphabet=CYRILLIC + LATIN_EXTENDED)
gen.render()  # "äПрBüТлöMк"

# Свой набор символов
gen = StringGen(r"\w{5}", alphabet="абвгдеж")
gen.render()  # "гдабе"
```

Предустановки будут определять замену для `\w`, `\d`, `\s`, `.`:
- `CYRILLIC` — `\w` → `[а-яА-ЯёЁ0-9_]`, `\d` → `[0-9]`, и т.д.
- `CJK` — `\w` → CJK Unified Ideographs (U+4E00–U+9FFF)
- `LATIN_EXTENDED` — `\w` → Latin + дополнительные символы (ä, ö, ü, ñ, ç…)

#### Вариант B: Explicit Unicode-диапазоны в самом regex

Пользователь уже может писать `[а-яА-Я]{10}` — но `\w` всё равно останется ASCII.
Этот вариант — просто задокументировать текущие возможности и улучшить поддержку
Unicode-диапазонов в `[...]` (сейчас уже работает через `RANGE` opcode).

#### Вариант C: Callback / маппинг для категорий

```python
gen = StringGen(r"\w{10}", categories={
    "word": "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ",
    "digit": "0123456789",
    "space": " \t\n",
})
gen.render()  # "ЩпРвбТлОмК"
```

**Рекомендация:** Вариант A — самый удобный для пользователя. Вариант C — самый гибкий. Можно совместить: вариант A реализовать поверх варианта C (предустановки — это готовые маппинги).

**Реализованные предустановки в модуле `string_gen/alphabets.py` (22 пресета):**

| Константа | Описание |
|-----------|----------|
| `ASCII` | `string.ascii_letters` (по умолчанию) |
| `CYRILLIC` | Русские буквы (а-я, А-Я, ё, Ё) |
| `GREEK` | Греческий алфавит (α-ω, Α-Ω) |
| `LATIN_EXTENDED` | ASCII + диакритические символы (ä, ñ, ç, ø…) |
| `HIRAGANA` | Японская хирагана |
| `KATAKANA` | Японская катакана |
| `CJK` | CJK Unified Ideographs (китайский, японские кандзи) |
| `HANGUL` | Корейские слоги |
| `ARABIC` | Арабское письмо |
| `DEVANAGARI` | Деванагари (хинди, маратхи, непальский) |
| `THAI` | Тайское письмо |
| `HEBREW` | Иврит |
| `BENGALI` | Бенгальское письмо |
| `TAMIL` | Тамильское письмо |
| `TELUGU` | Телугу |
| `GEORGIAN` | Грузинское письмо |
| `ARMENIAN` | Армянское письмо |
| `ETHIOPIC` | Эфиопское письмо (амхарский) |
| `MYANMAR` | Мьянманское/бирманское письмо |
| `SINHALA` | Сингальское письмо |
| `GUJARATI` | Гуджарати |
| `PUNJABI` | Пенджаби (гурмукхи) |

---

### 3. CLI-интерфейс (приоритет: самый низкий)

**Проблема:** Нет возможности быстро сгенерировать строки из терминала без написания скрипта.

**Решение:** Добавить `__main__.py` и console_scripts entry point.

```bash
# Одна строка
string-gen '\d{4}-\d{4}'
# 3842-1957

# Несколько строк
string-gen -n 5 '[A-Z]{3}-\d{3}'
# XKR-839
# BNQ-271
# JYL-054
# WMT-692
# AFZ-418

# Уникальные строки
string-gen -u 3 '\d{2}'
# 47
# 12
# 83

# С seed для воспроизводимости
string-gen -s 42 '\w{10}'

# Разделитель
string-gen -n 5 -d ',' '\d{3}'
# 384,195,726,413,058
```

**Реализация:**
- `string_gen/__main__.py` с `argparse`
- Entry point `string-gen` в `pyproject.toml`
- Аргументы: `-n/--count`, `-u/--unique`, `-s/--seed`, `-d/--delimiter`

---

### 4. Подсчёт количества возможных совпадений (приоритет: средний) ✅ реализовано

**Проблема:** Нет способа узнать, сколько уникальных строк может сгенерировать паттерн. Это полезно для `render_set()` — чтобы заранее знать, возможно ли получить N уникальных строк.

**Решение:** Метод `count()` на `StringGen`.

```python
gen = StringGen(r"[01]{3}")
gen.count()  # 8

gen = StringGen(r"\d")
gen.count()  # 10

gen = StringGen(r"\w+")
gen.count()  # math.inf
```

**Реализация:**
- Рекурсивный обход AST с подсчётом комбинаций
- Для безграничных квантификаторов (`+`, `*`) — возвращать `math.inf`
- Использовать в `render_set()` для раннего `ValueError` если `count > gen.count()`

**Заметка о производительности:** Для сложных паттернов с вложенными группами подсчёт
может быть дорогим. Рассмотреть кеширование результата (считать один раз, хранить в `_count`).

---

### 5. Перечисление всех совпадений (приоритет: высокий) ✅ реализовано

**Проблема:** Иногда нужны **все** возможные строки, а не случайные. Например, для exhaustive testing.

**Решение:** Метод-генератор `enumerate()`.

```python
gen = StringGen(r"[ab]{2}")
list(gen.enumerate())  # ['aa', 'ab', 'ba', 'bb']

gen = StringGen(r"(yes|no)")
list(gen.enumerate())  # ['yes', 'no']
```

**Реализация:**
- Генератор, обходящий AST и yield'ящий все комбинации через `itertools.product`
- Для бесконечных паттернов — параметр `max_length` для ограничения

---

### 6. Pytest-плагин (приоритет: низкий)

**Проблема:** Для тестирования приходится вручную создавать `StringGen` в каждом тесте.

**Решение:** Опциональный pytest-плагин с фикстурой и маркером.

```python
# Фикстура
def test_example(string_gen):
    email = string_gen(r"[a-z]{5,10}@(gmail|yahoo)\.com")
    assert "@" in email

# Маркер для параметризации
@pytest.mark.string_gen(r"\d{4}", count=5)
def test_codes(generated_string):
    assert len(generated_string) == 4
```

**Реализация:**
- Отдельный пакет `pytest-string-gen` или встроенный плагин через entry point
- Фикстура `string_gen` — фабрика, создающая `StringGen` и вызывающая `render()`

---

### 7. Настраиваемый лимит для безграничных квантификаторов (приоритет: высокий) ✅ реализовано

**Проблема:** `*`, `+`, `{n,}` захардкожены с максимумом 100. Нет способа изменить это ни локально, ни глобально.

**Варианты реализации:**

#### Вариант A: Параметр в конструкторе `StringGen`

```python
gen = StringGen(r"\w+", max_repeat=10)
gen.render()  # строка длиной 1–10
```

Плюсы: просто, явно, каждый инстанс независим.
Минусы: нужно передавать в каждый `StringGen()`.

#### Вариант B: Глобальная настройка через модуль-level конфигурацию

```python
import string_gen

# Глобально для всех новых инстансов
string_gen.configure(max_repeat=20)

gen = StringGen(r"\w+")
gen.render()  # строка длиной 1–20

# Локальный override имеет приоритет
gen2 = StringGen(r"\w+", max_repeat=5)
gen2.render()  # строка длиной 1–5
```

Плюсы: настроил один раз — работает везде. Локальный override сохраняется.
Минусы: глобальное состояние, нужно аккуратно с тестами.

#### Вариант C: Context manager для временной настройки

```python
import string_gen

# Глобальный дефолт
string_gen.configure(max_repeat=50)

# Временный override для блока кода
with string_gen.settings(max_repeat=5):
    gen = StringGen(r"\w+")
    gen.render()  # строка длиной 1–5

# Вне контекста — снова 50
gen2 = StringGen(r"\w+")
gen2.render()  # строка длиной 1–50
```

Плюсы: удобно для тестов, нет побочных эффектов за пределами блока.
Минусы: сложнее реализовать, thread-safety вопрос.

#### Вариант D: Комбинация A + B (рекомендация)

Все три уровня настройки с чётким приоритетом:

```
Приоритет: параметр конструктора > configure() > дефолт (100)
```

```python
import string_gen

# 1. Дефолт — 100 (как сейчас)
gen = StringGen(r"\w+")  # max_repeat=100

# 2. Глобальная настройка
string_gen.configure(max_repeat=20)
gen = StringGen(r"\w+")  # max_repeat=20

# 3. Локальный override
gen = StringGen(r"\w+", max_repeat=5)  # max_repeat=5
```

**Реализация варианта D:**
- Модуль-level `_config` dict с дефолтами
- Функция `configure(**kwargs)` обновляет `_config`
- `StringGen.__init__` принимает `max_repeat=None`, при `None` берёт из `_config`
- В будущем через `configure()` можно будет добавить и другие настройки (alphabet, seed и т.д.)

**Что ещё можно настраивать через `configure()`:**
- `max_repeat` — лимит для `*`, `+`, `{n,}`
- `alphabet` — дефолтный алфавит (из пункта 2)
- `seed` — глобальный seed

---

### 8. Include / Exclude символов (приоритет: низкий)

**Проблема:** Нет способа гарантировать присутствие определённых символов или исключить нежелательные.

**Решение:** Параметры `include` и `exclude` в `render()`.

```python
gen = StringGen(r"[a-z]{10}")

# Гарантировать наличие символа
gen.render(include="xyz")  # обязательно содержит x, y и z

# Исключить символы
gen.render(exclude="aeiou")  # без гласных
```

---

### 9. Встроенные паттерны / пресеты (приоритет: низкий) ✅ реализовано

**Проблема:** Пользователи часто генерируют одни и те же типы данных. Каждый раз приходится писать regex вручную и думать, правильный ли он.

**Решение:** Модуль `string_gen.patterns` с готовыми паттернами.

```python
from string_gen import StringGen
from string_gen.patterns import UUID4, HEX_COLOR, IPV4

gen = StringGen(UUID4)
gen.render()  # "a3f2b1c4-5d6e-4f7a-8b9c-0d1e2f3a4b5c"
```

**Предлагаемые паттерны (исследование):**

Ниже — паттерны, отобранные по частоте использования в тестировании. Критерий отбора: паттерн должен генерировать **валидные** данные (не просто похожие строки), и его regex должен быть достаточно сложным, чтобы пользователю было лениво писать его каждый раз.

#### Идентификаторы

| Константа | Пример вывода | Regex | Обоснование |
|-----------|---------------|-------|-------------|
| `UUID4` | `a3f2b1c4-5d6e-4f7a-8b9c-0d1e2f3a4b5c` | `[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}` | Сложный паттерн, часто нужен в тестах. Версия 4 обязывает `4` в 3-й группе и `[89ab]` в 4-й |
| `OBJECT_ID` | `507f1f77bcf86cd799439011` | `[a-f0-9]{24}` | MongoDB ObjectId — 24 hex-символа |

#### Сетевые

| Константа | Пример вывода | Regex | Обоснование |
|-----------|---------------|-------|-------------|
| `IPV4` | `192.168.1.42` | `(25[0-5]\|2[0-4]\d\|1\d{2}\|[1-9]\d\|\d)\.(...)\.(.)\.(.)` | Генерирует **валидные** IPv4 (0–255 в каждом октете). Писать вручную мучительно |
| `IPV6_SHORT` | `a3f2:b1c4:5d6e:4f7a:8b9c:0d1e:2f3a:4b5c` | `[a-f0-9]{1,4}(:[a-f0-9]{1,4}){7}` | Упрощённый IPv6 без сжатия `::` |
| `MAC_ADDRESS` | `a3:f2:b1:c4:5d:6e` | `[a-f0-9]{2}(:[a-f0-9]{2}){5}` | MAC-адрес |

#### Веб

| Константа | Пример вывода | Regex | Обоснование |
|-----------|---------------|-------|-------------|
| `HEX_COLOR` | `#a3f2b1` | `#[a-fA-F0-9]{6}` | Часто нужен в UI-тестировании |
| `HEX_COLOR_SHORT` | `#a3f` | `#[a-fA-F0-9]{3}` | Короткая форма |
| `SLUG` | `my-awesome-post` | `[a-z][a-z0-9]*(-[a-z0-9]+){1,5}` | URL-slug для тестов CMS / блогов |

#### Форматы данных

| Константа | Пример вывода | Regex | Обоснование |
|-----------|---------------|-------|-------------|
| `SEMVER` | `2.14.3` | `(0\|[1-9]\d*)\.(0\|[1-9]\d*)\.(0\|[1-9]\d*)` | Semantic Versioning |
| `DATE_ISO` | `2024-03-15` | `20[2-3]\d-(0[1-9]\|1[0-2])-(0[1-9]\|[12]\d\|3[01])` | ISO 8601 дата (2020–2039) |
| `TIME_24H` | `14:32:07` | `([01]\d\|2[0-3]):[0-5]\d:[0-5]\d` | Время в 24-часовом формате |

#### Безопасность / Аутентификация

| Константа | Пример вывода | Regex | Обоснование |
|-----------|---------------|-------|-------------|
| `JWT_LIKE` | `eyJhb.eyJzd.SflKx` | `[A-Za-z0-9_-]{20,40}\.[A-Za-z0-9_-]{20,60}\.[A-Za-z0-9_-]{20,40}` | Структура JWT-токена (не валидный, но правильной формы) |
| `API_KEY` | `sk_live_a3f2b1c45d6e4f7a8b9c` | `(sk\|pk)_(live\|test)_[a-zA-Z0-9]{20}` | Stripe-подобный API ключ |

**Паттерны, которые НЕ стоит включать:**
- `EMAIL` — слишком много вариаций, лучше пользователь напишет конкретный формат
- `PHONE` — специфичен для страны, нет универсального паттерна
- `CREDIT_CARD` — нужен алгоритм Луна, regex недостаточно
- `URL` — слишком сложный regex, лучше собирать из частей

---

### 10. Weighted-генерация (приоритет: низкий)

**Проблема:** В альтернациях (`a|b|c`) все варианты равновероятны. Иногда нужно смещение.

**Решение:** Поддержка весов через специальный синтаксис или API.

```python
# Через API
gen = StringGen(r"(success|error|timeout)")
gen.render(weights=[0.7, 0.2, 0.1])

# Или через метод
gen.with_weights({0: 0.7, 1: 0.2, 2: 0.1})
```

---

## Инфраструктурные улучшения

### 11. Документация (приоритет: средний) ✅ реализовано

**Инструменты:**
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) — стандарт для Python-библиотек (FastAPI, Pydantic, uv, ruff используют его)
- [mkdocstrings](https://mkdocstrings.github.io/) — автогенерация API Reference из docstrings
- Хостинг: GitHub Pages (бесплатно, CI через GitHub Actions)

**Структура документации:**

```
docs/
├── index.md              # Главная: описание, установка, быстрый старт
├── guide/
│   ├── getting-started.md  # Установка, первый пример
│   ├── patterns.md         # Поддерживаемый синтаксис regex с примерами
│   ├── generation.md       # render(), render_list(), render_set(), итераторы
│   ├── reproducibility.md  # seed, воспроизводимость результатов
│   ├── operators.md        # ==, |, bool()
│   └── configuration.md    # configure(), max_repeat, alphabets
├── reference/
│   ├── api.md              # Автогенерация из docstrings (mkdocstrings)
│   ├── patterns.md         # Справочник встроенных пресетов
│   └── alphabets.md        # Справочник алфавитов
├── examples/
│   └── cookbook.md          # Рецепты: UUID, email, тестовые данные, i18n
└── changelog.md            # Ссылка на GitHub Releases
```

**Файл `mkdocs.yml`:**

```yaml
site_name: string-gen
site_url: https://tolstislon.github.io/string-gen/
repo_url: https://github.com/tolstislon/string-gen
theme:
  name: material
  features:
    - content.code.copy
    - navigation.sections
    - navigation.expand
plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          options:
            show_source: true
            docstring_style: sphinx
markdown_extensions:
  - pymdownx.highlight
  - pymdownx.superfences
  - admonition
```

**CI для документации (`.github/workflows/docs.yml`):**
- Триггер: push в main
- Build: `mkdocs build`
- Deploy: `mkdocs gh-deploy`

---

### 12. Бенчмарки (приоритет: самый низкий)

**Цель:** Измерить производительность string-gen vs конкурентов и отслеживать регрессии.

**Инструменты:**
- [pytest-benchmark](https://pypi.org/project/pytest-benchmark/) — локальные бенчмарки
- [CodSpeed](https://codspeed.io/) + [pytest-codspeed](https://github.com/CodSpeedHQ/pytest-codspeed) — CI-бенчмарки с отслеживанием регрессий в PR

**Что измерять:**

#### Набор паттернов (от простых к сложным)

| Паттерн | Описание | Почему важен |
|---------|----------|--------------|
| `\d{10}` | Простой repeat | Базовая операция |
| `[a-zA-Z0-9]{50}` | Character class | Частый use case |
| `[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}` | UUID | Реальный сложный паттерн |
| `(A\|B)\d{4}(\.\|-)\d{1}` | Alternation + groups | Ветвление |
| `(?P<d>\d)_(?P=d)` | Backreference | Кеширование групп |
| `\w+` | Unbounded quantifier | Нагрузка на repeat |
| `([A-Z][a-z]{1,15}\n){4,}[^\s]\w{1,15}\n\W{3}` | Сложный комбинированный | Стресс-тест |

#### Операции для бенчмарка

| Операция | Что измеряем |
|----------|-------------|
| `render()` × 1 | Латентность одного вызова |
| `render_list(1000)` | Throughput массовой генерации |
| `render_set(100)` | Overhead уникальности |
| `StringGen(pattern)` | Время инициализации (компиляция regex) |

#### Версии Python

| Версия | Зачем |
|--------|-------|
| 3.8 | Минимальная поддерживаемая (sre_parse) |
| 3.12 | Текущий стабильный (re._parser) |
| 3.14 | Новейший (возможные оптимизации) |
| PyPy 3.10 | JIT — ожидается значительный прирост |

#### Сравнение с конкурентами

| Библиотека | Эквивалент `render()` |
|------------|----------------------|
| string-gen | `StringGen(pattern).render()` |
| rstr | `rstr.xeger(pattern)` |
| exrex | `exrex.getone(pattern)` |

**Структура файлов:**

```
benchmarks/
├── conftest.py           # Фикстуры с паттернами
├── test_render.py        # Бенчмарки render/render_list/render_set
├── test_init.py          # Бенчмарк инициализации
└── test_vs_competitors.py  # Сравнение с rstr, exrex
```

---

### 13. `__str__` метод (приоритет: на подумать)

**Идея:** `__str__` вызывает `render()`, позволяя использовать в f-строках: `f"Code: {gen}"`.

**Контраргумент:** Каждый `print(gen)` или `f"{gen}"` даёт **разное значение**. Это неочевидно и нарушает ожидание, что `str(obj)` — стабильное представление объекта. Может привести к трудноуловимым багам при логировании и отладке.

**Решение:** Пока оставить `__str__ = __repr__`. Вернуться к обсуждению если появится реальный запрос от пользователей.

---

## Дорожная карта по версиям

### v0.2.0 — Итераторы, max_repeat и configure() ✅
- [x] `__iter__` / `__next__` протокол
- [x] `stream(count)` генератор
- [x] Функция `configure()` для глобальных настроек
- [x] Параметр `max_repeat` (через конструктор и `configure()`)

### v0.3.0 — Перечисление и подсчёт ✅
- [x] `enumerate()` — перечисление всех совпадений
- [x] `count()` — подсчёт возможных совпадений
- [x] Ранний `ValueError` в `render_set()` когда `count > gen.count()`

### v0.4.0 — Кастомные алфавиты ✅
- [x] Модуль `string_gen/alphabets.py` с 22 предустановками
- [x] Параметр `alphabet` в `StringGen` и `configure()`
- [x] Функция `reset()` для сброса глобальных настроек
- [ ] Маппинг `categories` для полного контроля

### v0.5.0 — Пресеты и документация
- [x] Модуль `string_gen/patterns.py` с готовыми паттернами
- [x] Документация на Material for MkDocs + GitHub Pages
- [x] Cookbook с рецептами

### v0.6.0 — Экосистема
- [ ] Include/Exclude символов
- [ ] Pytest-плагин
- [ ] Weighted-генерация

### v1.0.0 — Стабильный релиз
- [ ] CLI-интерфейс
- [ ] Бенчмарки и сравнение с конкурентами
- [ ] Стабилизация API
- [ ] Полная документация

---

## Источники и вдохновение

- [rstr](https://github.com/leapfrogonline/rstr) — convenience-методы, include/exclude, кастомные алфавиты
- [exrex](https://github.com/asciimoo/exrex) — enumerate, count, simplify, CLI, Unicode
- [hypothesis from_regex](https://hypothesis.readthedocs.io/) — Unicode, alphabet parameter
- [xeger](https://pypi.org/project/xeger/) — минималистичный подход
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) — документация
- [CodSpeed](https://codspeed.io/) — CI-бенчмарки
