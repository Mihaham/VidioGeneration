import requests
import threading
import time
import uuid
import os
from pathlib import Path
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
import requests
from videogeneration.config import GIGACHAT_CREDENTIALS, SALUT_CREDENTIALS, SALUT_CLIENT_ID, VOICES
from videogeneration.utils import get_next_free_path
from loguru import logger
import base64
import random

class SalutWrapper:
    def __init__(self, authorization_key = SALUT_CREDENTIALS, scope='SALUTE_SPEECH_PERS'):
        self.bearer_token = None
        self.token_url = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
        self.tts_url = "https://smartspeech.sber.ru/rest/v1/text:synthesize"
        self.scope = scope
        self.api_key = authorization_key
        self.uuid = str(uuid.uuid4())
        self.running = True
        self.token_ready = threading.Event()  # Событие для синхронизации
        self.token_thread = self.start()
        self.voices = VOICES

        # Ждем первичное получение токена 10 секунд
        if not self.token_ready.wait(timeout=10):
            logger.error("Initial token not received!")

    def start(self):
        thread = threading.Thread(target=self.poll_token)
        thread.daemon = True
        thread.start()
        return thread

    def poll_token(self):
        headers = {
            'Authorization': f'Basic {self.api_key}',
            'RqUID': self.uuid,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {'scope': self.scope}
        
        while self.running:
            try:
                expires_at = self.update_token(headers, data)
                if expires_at // 1000 - time.time() > 0:
                    sleep_time = max(expires_at //1000 - time.time(), 60)  # Обновляем на минуту раньше
                    logger.success(f"Token received. Next refresh in {sleep_time} sec")
                    self.token_ready.set()  # Сигнализируем о готовности токена
                else:
                    sleep_time = 5
                
                time.sleep(sleep_time)
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                time.sleep(5)

    def update_token(self, headers, data):
        try:
            response = requests.post(
                self.token_url,
                headers=headers,
                data=data,
                verify=False,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.bearer_token = token_data['access_token']
                logger.debug("Successfully obtained new bearer token")
                return int(token_data['expires_at'])
            else:
                logger.error(f"Token error {response.status_code}: {response.text}")
                return 0
            
        except Exception as e:
            logger.error(f"Token update exception: {e}")
            return 0

    def text_to_audio(self, text, output_path, voice=None):
        if not self.bearer_token:
            logger.warning("No valid access token")
        
        
        headers = {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/text',
            'RqUID': str(uuid.uuid4()),
        }

        params = {
            'voice': random.choice(self.voices) if not voice else voice,  # Голос
            'format': 'wav16',       # Формат аудио
        }
        
        try:
            logger.debug(f"Sending request to api")
            response = requests.post(
                self.tts_url,
                headers=headers,
                params=params,
                data = text,
                verify=False,
                timeout=30
            )
            
            response.raise_for_status()
            logger.debug(f"We got the answer from the API")
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
                
            logger.success(f"Audio saved to {output_path}")
            return True
            
        except requests.HTTPError as e:
            logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            
        return False



def generate_audio_with_salut(prompt: str) -> str:
    # Создаем директорию для сохранения
    output_dir = Path("output/sound")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Генерация текста через GigaChat
    with GigaChat(credentials=GIGACHAT_CREDENTIALS, verify_ssl_certs=False) as giga:
        response = giga.chat(
            Chat(messages=[
                Messages(
                    role=MessagesRole.USER, 
                    content="""
                            Вы профессиональный русскоязычный сценарист. Жесткие правила:
                            1. ТОЛЬКО единый связный текст без списков и пунктов
                            2. Запрещены: 
                            - Нумерация (1., 2., 3.)
                            - Маркированные пункты
                            - Выделения жирным/курсивом
                            - Заголовки
                            - Разделители (---, ===)
                            3. Строго 20-25 предложений (~800 символов)
                            4. Плавные переходы между предложениями
                            5. Используй:
                            - Союзы (однако, тем временем, постепенно)
                            - Наречия времени (медленно, стремительно, затем)
                            - Причастные/деепричастные обороты
                            6. Каждые 3-5 предложений описывают один аспект визуала
                            7. Сохраняй хронологический порядок как в видео

                            Пример ПРАВИЛЬНОГО формата:
                            Камера медленно погружается в сердце мегаполиса будущего, где неоновые спирали танцуют в ритме с голографическими проекциями. На первом плане возникает силуэт воина, чей костюм излучает пульсирующее сияние сквозь сеть нанопроводов. С каждым шагом экзоскелет оживает: гидравлические суставы сжимаются с едва слышным шипением, а панели брони перестраиваются, адаптируясь к окружающей температуре. Вокруг нарастает симфония технологий — дроны-сканеры прочерчивают лазерные сетки над головой, пока голограммы рекламных таблоов мерцают в такт биению гигантских энергетических сердечников...
                            """
                ),
                Messages(
                    role=MessagesRole.USER, 
                    content=f"""
                                Сгенерируйте ЕДИНЫЙ текст для озвучки без разрывов и списков. Требования:
                                - Плавное описание сцен как в документальном фильме
                                - Естественные переходы между объектами (слева направо, фон->передний план)
                                - Хронология должна точно соответствовать видеоряду: {prompt}
                                - Каждое новое предложение развивает предыдущее
                                - Запрещены резкие скачки между темами

                                Начни сразу с описания первого кадра. Используй сложносочиненные предложения с союзами "в то время как", "по мере того как", "вслед за".
                            """
                )
            ])
        )
        generated_text = response.choices[0].message.content
        logger.success(f"Сгенерированный текст: {generated_text}")

    generator = SalutWrapper()

    audio_path = get_next_free_path("output/sound", prefix="sound_", suffix = '.wav')

    generator.text_to_audio(generated_text, audio_path)
    
    return str(audio_path), generated_text


def generate_audio_file(text, voice =None):
    generator = SalutWrapper()

    audio_path = get_next_free_path("output/sound", prefix="sound_", suffix='.wav')
    logger.info(f"Генерирую аудиофайл из текста: {text} c голосом {voice}")
    generator.text_to_audio(text, audio_path, voice = voice)
    return audio_path

if __name__ == "__main__":
    generator = SalutWrapper()

    audio_path = get_next_free_path("output/sound", prefix="sound_", suffix = '.wav')

    generator.text_to_audio("Большой русский текст", audio_path)