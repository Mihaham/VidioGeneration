import os
import re
import argparse

from pathlib import Path

def replace_tqdm_in_file(file_path: Path, custom_module: str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        return False



    # Замена вызовов tqdm.tqdm и tqdm.trange
    content = re.sub(r'\btqdm\.tqdm\b', 'SilentTqdm', content)
    content = re.sub(r'\btqdm\.trange\b', 'silent_trange', content)

    # Замена вызовов прямого импорта
    content = re.sub(r'\btrange\s*\(', 'silent_trange(', content)
    content = re.sub(r'\btqdm\s*\(', 'SilentTqdm(', content)

    content = add_import_statement(content, "from mytqdm import SilentTqdm, silent_trange")

    # Сохранение изменений
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def replace_logging_and_prints_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Счетчики замен
    replacements = {
        'print': 0,
        'logging_debug': 0,
        'logging_info': 0,
        'logging_warning': 0,
        'logging_error': 0,
        'logging_critical': 0,
        'logging_exception': 0,
        'logging_warn': 0
    }

    # Функция для замены с подсчетом
    def make_replacer(new_func, key):
        def replacer(match):
            replacements[key] += 1
            return f'{match.group(1)}{new_func}({match.group(3)})'

        return replacer

    # Улучшенные регулярки для замены
    patterns = [
        # Стандартный print (заменяем на logger.info)
        (r'(^|[^\w.])(print)\((.*?)\)',
         make_replacer('logger.info', 'print'),
         'logger.info'),

        # Методы logging (заменяем на соответствующие методы logger)
        (r'(^|[^\w])(logging\.debug)\((.*?)\)',
         make_replacer('logger.debug', 'logging_debug'),
         'logger.debug'),

        (r'(^|[^\w])(logging\.info)\((.*?)\)',
         make_replacer('logger.info', 'logging_info'),
         'logger.info'),

        (r'(^|[^\w])(logging\.warning)\((.*?)\)',
         make_replacer('logger.warning', 'logging_warning'),
         'logger.warning'),

        (r'(^|[^\w])(logging\.error)\((.*?)\)',
         make_replacer('logger.error', 'logging_error'),
         'logger.error'),

        (r'(^|[^\w])(logging\.critical)\((.*?)\)',
         make_replacer('logger.critical', 'logging_critical'),
         'logger.critical'),

        (r'(^|[^\w])(logging\.exception)\((.*?)\)',
         make_replacer('logger.exception', 'logging_exception'),
         'logger.exception'),

        # logging.warn (устаревший аналог warning)
        (r'(^|[^\w])(logging\.warn)\((.*?)\)',
         make_replacer('logger.warning', 'logging_warn'),
         'logger.warning')
    ]

    # Применяем все паттерны замены
    new_content = content
    for pattern, repl, _ in patterns:
        new_content = re.sub(
            pattern,
            repl,
            new_content,
            flags=re.DOTALL
        )

    # Обработка пустых вызовов
    new_content = re.sub(
        r'logger\.(info|debug|warning|error|critical|exception)\(\s*\)',
        r'logger.\1("")',
        new_content,
        flags=re.DOTALL
    )

    # Проверяем были ли замены
    has_replacements = any(count > 0 for count in replacements.values())
    if not has_replacements:
        return False

    # Проверяем наличие импорта loguru
    has_loguru_import = any(
        re.search(pattern, new_content, re.MULTILINE)
        for pattern in [
            r'^from\s+loguru\s+import\s+logger',
            r'^import\s+loguru\s*$',
            r'^from\s+loguru\s+import\s*\*'
        ]
    )

    # Добавляем импорт если нужно
    if not has_loguru_import:
        new_content = add_import_statement(new_content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True


def add_import_statement(content, name_of_import="from loguru import logger"):
    lines = content.splitlines()
    insert_index = 0
    in_docstring = False
    docstring_ended = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Завершаем обработку docstring если он закончился
        if in_docstring:
            if '"""' in line or "'''" in line:
                in_docstring = False
                docstring_ended = True
            continue

        # Проверяем начало docstring
        if not docstring_ended and (stripped.startswith('"""') or stripped.startswith("'''")):
            if stripped.count('"""') < 2 and stripped.count("'''") < 2:
                in_docstring = True
            continue

        # Пропускаем пустые строки, комментарии и кодировку
        if not stripped or stripped.startswith('#') or re.match(r'^#\s*-*\s*coding\s*[:=]', line):
            continue

        # Обрабатываем __future__ импорты
        if '__future__' in line:
            insert_index = i + 1
            continue

        # Если нашли не-специальную строку, останавливаемся
        insert_index = i
        break
    else:
        # Если дошли до конца, вставляем в конец
        insert_index = len(lines)

    # Вставляем импорт
    lines.insert(insert_index, name_of_import)

    # Добавляем пустую строку после импорта если нужно
    if insert_index < len(lines) - 1 and lines[insert_index + 1].strip() != '':
        lines.insert(insert_index + 1, '')

    return '\n'.join(lines)


def process_project(directory):
    exclude_dirs = {'venv', '.venv', 'env', '.env'}
    # Добавляем список исключаемых файлов
    exclude_files = {'mytqdm.py', 'deprecated_utils.py'}  # Здесь перечислите файлы для исключения

    for root, dirs, files in os.walk(directory):
        # Пропускаем системные папки виртуальных окружений
        if any(exclude_dir in root.split(os.sep) for exclude_dir in exclude_dirs):
            continue

        # Исключаем папки виртуальных окружений из дальнейшего обхода
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith('.py'):
                # Проверяем, не входит ли файл в исключения
                if file in exclude_files:
                    print(f'Пропущен файл (в списке исключений): {file}')
                    continue

                filepath = os.path.join(root, file)
                try:
                    modified1 = replace_logging_and_prints_in_file(filepath)
                    modified2 = replace_tqdm_in_file(Path(filepath), "mytqdm")
                    if modified1 and modified2:
                        print(f'Обновлен файл: {filepath}')
                except Exception as e:
                    print(f'Ошибка в файле {filepath}: {str(e)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', nargs='?', default='.',
                        help='Директория проекта (по умолчанию: текущая)')
    args = parser.parse_args()

    print('=== Замена print и logging на loguru ===')
    process_project(args.directory)
    print('=== Обработка завершена ===')