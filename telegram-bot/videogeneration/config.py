import os
from dotenv import load_dotenv
from pytz import timezone
from loguru import logger
load_dotenv()

GIGACHAT_CREDENTIALS = os.getenv('GIGACHAT_CREDENTIALS')
SALUT_CREDENTIALS = os.getenv('SALUT_CREDENTIALS')
SALUT_CLIENT_ID = os.getenv('SALUT_CLIENT_ID')
CA_BUNDLE_FILE = "russian_trusted_root_ca.cer"
PROMPT_TYPE = "SIMPLE" # "GIGACHAT" #
USE_PUBLIC = False
URL = "http://sd_webui_back:7860" if not USE_PUBLIC else ""
VOICES = ["Nec_24000", "Bys_24000", "May_24000", "Tur_24000", "Ost_24000", "Pon_24000"]
VOICES_DICT = {
    "👩 Наталья": "Nec_24000",
    "👨 Борис": "Bys_24000",
    "👩 Марфа": "May_24000",
    "👨 Тарас": "Tur_24000",
    "👩 Александра": "Ost_24000",
    "👨 Сергей": "Pon_24000",
    "👩 Kira (Английский язык)": "Kin_24000"
}
