import os
from pathlib import Path

TEMPLATE_env1 = """
# Админские credentials
POSTGRES_USER=admin
POSTGRES_PASSWORD=secure_admin_password
POSTGRES_DB=mydb

# Credentials для приложения
POSTGRES_APP_USER=app_user
POSTGRES_APP_PASSWORD=strong_app_password
"""

TEMPLATE_env2 = """
BOT_TOKEN=<YOUR TOKEN>
USER_ID=<OWNER ID>
TZ=Europe/Moscow
GIGACHAT_CREDENTIALS=<YOUR TOKEN>
SALUT_CREDENTIALS=<YOUR TOKEN>
"""


def init_project_structure():
    # Создание обязательных каталогов
    directories = [
        r"stable-diffusion\models\Stable-diffusion",
        r"telegram-bot\database\postgres_data",
        r"telegram-bot\fonts",
        r"telegram-bot\logs",
        r"telegram-bot\output",
    ]
    
    # Создание шаблонных файлов
    files = {
        r'telegram-bot\database\.env': TEMPLATE_env1,
        r'telegram-bot\.env': TEMPLATE_env2,
        r'telegram-bot\client_secrets.json': '',
        r'telegram-bot\russian_trusted_root_ca.cer' : ''
    }

    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dir_path}")

    for file_path, content in files.items():
        if not Path(file_path).exists():
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"Created template: {file_path}")

if __name__ == "__main__":
    init_project_structure()