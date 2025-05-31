import os
import re
import argparse


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


def add_import_statement(content):
    lines = content.splitlines()
    insert_index = 0

    # Ищем правильное место для вставки импорта
    for i, line in enumerate(lines):
        # Пропускаем пустые строки в начале файла
        if not line.strip():
            continue

        # Проверяем, можно ли пропустить эту строку
        if (line.startswith('#')
                or re.match(r'^#\s*-*\s*coding\s*[:=]', line)
                or '__future__' in line):
            insert_index = i + 1
            continue

        # Если нашли не-специальную строку, останавливаемся
        insert_index = i
        break
    else:
        # Если дошли до конца, вставляем в конец
        insert_index = len(lines)

    # Вставляем импорт
    lines.insert(insert_index, 'from loguru import logger')

    # Добавляем пустую строку после импорта если нужно
    if insert_index < len(lines) - 1 and lines[insert_index + 1].strip() != '':
        lines.insert(insert_index + 1, '')

    return '\n'.join(lines)


def process_project(directory):
    exclude_dirs = {'venv', '.venv', 'env', '.env'}

    for root, dirs, files in os.walk(directory):
        # Пропускаем системные папки виртуальных окружений
        if any(exclude_dir in root.split(os.sep) for exclude_dir in exclude_dirs):
            continue

        # Исключаем папки виртуальных окружений из дальнейшего обхода
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    modified = replace_logging_and_prints_in_file(filepath)
                    if modified:
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