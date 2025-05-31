# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import base64
import json
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from loguru import logger

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

from videogeneration.config import URL
from videogeneration.utils import get_next_free_path


class AsyncSDClient:
    """Асинхронный клиент для работы с Stable Diffusion API."""
    
    def __init__(self, base_url: str = URL):
        self.base_url = base_url
        self._session: Optional[aiohttp.ClientSession] = None
        self.cmd_flags: Optional[Dict[str, Any]] = None
        self._important_flags: Dict[str, Any] = {}

        self._api_data: Dict[str, Any] = {
            'samplers': [],
            'schedulers': [],
            'upscalers': [],
            'latent_upscale_modes': [],
            'sd_models': [],
            'hypernetworks': [],
            'face_restorers': [],
            'realesrgan_models': [],
            'prompt_styles': [],
            'embeddings': [],
            'loras': []
        }

        self._refresh_actions = {
            'embeddings': ('sdapi/v1/refresh-embeddings', 'embeddings'),
            'checkpoints': ('sdapi/v1/refresh-checkpoints', 'sd_models'),
            'vae': ('sdapi/v1/refresh-vae', 'sd_models'),
            'loras': ('sdapi/v1/refresh-loras', 'hypernetworks')
        }
        
        logger.debug("Initialized AsyncSDClient with base URL: {}", base_url)

    async def __aenter__(self) -> AsyncSDClient:
        """Контекстный менеджер для инициализации сессии."""
        logger.info("Creating aiohttp client session")
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60*60*10))
        return self

    async def __aexit__(self, *exc) -> None:
        """Завершение работы контекстного менеджера."""
        logger.info("Closing aiohttp client session")
        await self._session.close()

    async def initialize(self) -> None:
        """Инициализация клиента с загрузкой основных данных API."""
        await self._fetch_multiple_endpoints([
            ('samplers', 'sdapi/v1/samplers'),
            ('schedulers', 'sdapi/v1/schedulers'),
            ('upscalers', 'sdapi/v1/upscalers'),
            ('latent_upscale_modes', 'sdapi/v1/latent-upscale-modes'),
            ('sd_models', 'sdapi/v1/sd-models'),
            ('hypernetworks', 'sdapi/v1/hypernetworks'),
            ('face_restorers', 'sdapi/v1/face-restorers'),
            ('realesrgan_models', 'sdapi/v1/realesrgan-models'),
            ('prompt_styles', 'sdapi/v1/prompt-styles'),
            ('embeddings', 'sdapi/v1/embeddings'),
        ])
        logger.success("Completed initial API data loading")

    async def refresh_resources(self, resource_type: str) -> str:
        """
        Обновление указанного типа ресурсов
        Допустимые типы: embeddings, checkpoints, vae, loras
        """
        if resource_type not in self._refresh_actions:
            raise ValueError(f"Invalid resource type: {resource_type}. Valid types: {list(self._refresh_actions.keys())}")

        endpoint, cache_key = self._refresh_actions[resource_type]
        logger.info("Starting refresh of {}", resource_type)

        try:
            response_text = await self._post_request(endpoint)
            await self._update_cache(cache_key)
            logger.success("Successfully refreshed {}", resource_type)
            return response_text
        except Exception as e:
            logger.error("Failed to refresh {}: {}", resource_type, e)
            raise

    async def _post_request(self, endpoint: str) -> str:
        """Универсальный метод для POST-запросов без тела"""
        url = f"{self.base_url}/{endpoint}"
        logger.debug("Making POST request to {}", url)

        try:
            async with self._session.post(url, json={}) as response:
                response.raise_for_status()
                text = await response.text()
                logger.debug("Received response: {}", text)
                return text
        except aiohttp.ClientResponseError as e:
            logger.error("Refresh error: HTTP {} - {}", e.status, e.message)
            raise
        except aiohttp.ClientError as e:
            logger.critical("Connection error: {}", str(e))
            raise

    async def _update_cache(self, cache_key: str) -> None:
        """Обновление кэша после успешного обновления ресурсов"""
        endpoints_map = {
            'embeddings': 'sdapi/v1/embeddings',
            'sd_models': 'sdapi/v1/sd-models',
            'hypernetworks': 'sdapi/v1/hypernetworks'
        }

        if cache_key in endpoints_map:
            logger.debug("Updating cache for {}", cache_key)
            self._api_data[cache_key] = await self._get_request(endpoints_map[cache_key])

    async def _fetch_multiple_endpoints(self, endpoints: List[Tuple[str, str]]) -> None:
        """Пакетная загрузка данных из нескольких эндпоинтов"""
        for data_key, endpoint in endpoints:
            try:
                self._api_data[data_key] = await self._get_request(endpoint)
                logger.debug("Loaded {} items from {}", len(self._api_data[data_key]), endpoint)
            except Exception as e:
                logger.error("Failed to load {}: {}", endpoint, e)
                self._api_data[data_key] = []

    async def _get_request(self, endpoint: str) -> List[Dict]:
        """Универсальный метод для GET-запросов"""
        url = f"{self.base_url}/{endpoint}"
        logger.debug("Fetching data from {}", url)
        
        try:
            async with self._session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                logger.success("Successfully received data from {}", endpoint)
                return data
        except aiohttp.ClientResponseError as e:
            logger.error("API error {}: {}", e.status, e.message)
            raise
        except Exception as e:
            logger.exception("Unexpected error in GET request")
            raise

    @property
    def sd_models(self) -> List[Dict]:
        """Доступные SD модели"""
        return self._api_data['sd_models']
    
    @property
    def hypernetworks(self) -> List[Dict]:
        """Гиперсети"""
        return self._api_data['hypernetworks']
    
    @property
    def face_restorers(self) -> List[Dict]:
        """Модели восстановления лиц"""
        return self._api_data['face_restorers']
    
    @property
    def realesrgan_models(self) -> List[Dict]:
        """ESRGAN модели апскейла"""
        return self._api_data['realesrgan_models']
    
    @property
    def prompt_styles(self) -> List[Dict]:
        """Стили промптов"""
        return self._api_data['prompt_styles']
    
    @property
    def embeddings(self) -> List[Dict]:
        """Текстовые инверсии"""
        return self._api_data['embeddings']

    @property
    def latent_upscale_modes(self) -> List[Dict]:
        """Режимы латентного апскейла"""
        return self._api_data['latent_upscale_modes']

    @property
    def samplers(self) -> List[Dict]:
        """Сэмплеры"""
        return self._api_data['samplers']
    
    @property
    def schedulers(self) -> List[Dict]:
        """Планировщики"""
        return self._api_data['schedulers']
    
    @property
    def upscalers(self) -> List[Dict]:
        """Апскейлеры"""
        return self._api_data['upscalers']

    async def get_cmd_flags(self, cache: bool = True) -> Dict[str, Any]:
        """Получение и кэширование конфигурационных флагов"""
        if cache and self.cmd_flags is not None:
            logger.debug("Returning cached cmd flags")
            return self.cmd_flags

        logger.info("Requesting command line flags from API")
        try:
            async with self._session.get(f"{self.base_url}/sdapi/v1/cmd-flags") as response:
                response.raise_for_status()
                self.cmd_flags = await response.json()
                self._extract_important_flags()
                logger.success("Successfully received cmd flags")
                return self.cmd_flags
        except aiohttp.ClientResponseError as e:
            logger.error("Failed to get cmd flags: HTTP {} - {}", e.status, e.message)
            raise
        except Exception as e:
            logger.exception("Unexpected error while fetching cmd flags")
            raise

    def _extract_important_flags(self) -> None:
        """Извлечение важных параметров конфигурации"""
        important_keys = {
            'models_dir', 'config', 'ckpt', 'vae_dir', 'lora_dir',
            'embeddings_dir', 'hypernetwork_dir', 'port', 'precision',
            'xformers', 'medvram', 'lowvram', 'always_batch_cond_uncond'
        }
        self._important_flags = {
            k: self.cmd_flags.get(k, "")
            for k in important_keys
        }
        logger.debug("Extracted {} important flags", len(self._important_flags))

    @property
    def important_flags(self) -> Dict[str, Any]:
        """Основные параметры конфигурации"""
        if not self._important_flags:
            raise ValueError("Flags not loaded yet, call get_cmd_flags first")
        return self._important_flags

    def get_model_paths(self) -> Dict[str, Path]:
        """Получение путей к моделям"""
        paths = {}
        try:
            paths['models'] = Path(self.important_flags.get('models_dir', ''))
            paths['embeddings'] = Path(self.important_flags.get('embeddings_dir', ''))
            paths['lora'] = Path(self.important_flags.get('lora_dir', ''))
            paths['hypernetwork'] = Path(self.important_flags.get('hypernetwork_dir', ''))

            for name, path in paths.items():
                if not path or str(path) == ".":
                    logger.warning("Empty path detected for {}: {}", name, path)
                    paths[name] = Path("")
        except Exception as e:
            logger.error("Failed to parse model paths: {}", e)
            raise ValueError("Invalid path configuration") from e
        return paths

    async def get_system_info(self) -> Dict:
        """Получение информации о системе"""
        logger.debug("Fetching system information")
        system_info = await self._request("sdapi/v1/system-info", {})
        logger.debug("Successfully retrieved system information")
        return system_info

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Получение статистики использования памяти"""
        endpoint = "sdapi/v1/memory"
        logger.info("Requesting memory statistics")
        
        try:
            memory_data = await self._get_request(endpoint)
            logger.success("Received memory stats")
            return memory_data
        except Exception as e:
            logger.error("Failed to get memory stats: {}", str(e))
            raise

    async def get_progress(self, skip_current_image: bool = False) -> Optional[Dict]:
        """Получение информации о текущем прогрессе"""
        params = {"skip_current_image": str(skip_current_image).lower()}
        
        try:
            async with self._session.get(
                f"{self.base_url}/sdapi/v1/progress",
                params=params,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"Progress check failed: HTTP {e.status} {e.message}")
            return None
        except asyncio.TimeoutError:
            logger.warning("Progress request timed out")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error getting progress: {str(e)}")
            return None

    async def interrupt(self) -> str:
        """Прерывание текущей генерации"""
        return await self._send_control_request("sdapi/v1/interrupt")

    async def skip(self) -> str:
        """Пропуск текущей задачи"""
        return await self._send_control_request("sdapi/v1/skip")

    async def _send_control_request(self, endpoint: str) -> str:
        """Общий метод для управляющих запросов"""
        logger.info("Sending control request to {}", endpoint)
        
        try:
            async with self._session.post(
                f"{self.base_url}/{endpoint}",
                json={}
            ) as response:
                response.raise_for_status()
                result = await response.text()
                logger.success("Control request {} succeeded", endpoint)
                return result.strip()
        except aiohttp.ClientResponseError as e:
            error_msg = f"Control request failed: HTTP {e.status} - {e.message}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Control request error: {str(e)}"
            logger.critical(error_msg)
            return error_msg

    async def txt2img(self, **kwargs) -> List[bytes]:
        """Генерация изображений по тексту"""
        self._validate_required_params(kwargs, {'prompt', 'steps', 'width', 'height'})
        logger.info("Starting txt2img with params: {}", self._sanitize_log_data(kwargs))
        response = await self._request("sdapi/v1/txt2img", kwargs)
        return self._decode_images(response)

    async def img2img(self, init_images: List[bytes], **kwargs) -> List[bytes]:
        """Редактирование изображений"""
        if not init_images:
            raise ValueError("At least one init image required")
            
        payload = {
            "init_images": [self._b64_encode(img) for img in init_images],
            **kwargs
        }
        logger.info("Starting img2img with {} images", len(init_images))
        response = await self._request("sdapi/v1/img2img", payload)
        return self._decode_images(response)

    async def extra_single_image(
        self, 
        image: bytes,
        upscaler: str = "R-ESRGAN 4x+",
        upscaling_resize: float = 2.0
    ) -> bytes:
        """Улучшение одного изображения"""
        payload = {
            "image": self._b64_encode(image),
            "upscaler_1": upscaler,
            "resize_mode": 0,
            "upscaling_resize": upscaling_resize
        }
        response = await self._request("sdapi/v1/extra-single-image", payload)
        return self._decode_images(response)[0]

    async def extra_batch_images(
        self,
        images: List[bytes],
        upscaler_1: str = "None",
        upscaler_2: str = "None",
        upscaling_resize: float = 2.0,
        upscaling_resize_w: int = 512,
        upscaling_resize_h: int = 512,
        **kwargs
    ) -> List[bytes]:
        """Пакетное улучшение изображений"""
        payload = {
            "resize_mode": 0,
            "show_extras_results": True,
            "gfpgan_visibility": 0,
            "codeformer_visibility": 0,
            "codeformer_weight": 0,
            "upscaling_resize": upscaling_resize,
            "upscaling_resize_w": upscaling_resize_w,
            "upscaling_resize_h": upscaling_resize_h,
            "upscaling_crop": True,
            "upscaler_1": upscaler_1,
            "upscaler_2": upscaler_2,
            "extras_upscaler_2_visibility": 0,
            "upscale_first": False,
            "imageList": [
                {
                    "data": self._b64_encode(img),
                    "name": f"image_{i}.png"
                } for i, img in enumerate(images)
            ],
            **kwargs
        }
        
        logger.info(
            "Batch upscaling {} images with {} upscaler",
            len(images),
            upscaler_1
        )
        
        response = await self._request("sdapi/v1/extra-batch-images", payload)
        return self._decode_images(response)

    async def png_info(self, image: bytes) -> Dict:
        """Получение метаданных PNG"""
        payload = {"image": self._b64_encode(image)}
        return await self._request("sdapi/v1/png-info", payload)

    async def _request(self, endpoint: str, payload: Dict) -> Dict:
        """Базовый метод для выполнения запросов"""
        url = f"{self.base_url}/{endpoint}"
        logger.debug("Making POST request to {}", url)
        
        try:
            async with self._session.post(url, json=payload) as response:
                logger.debug("Received response status: {}", response.status)
                response.raise_for_status()
                json_data = await response.json()
                logger.success("Request to {} completed successfully", endpoint)
                return json_data
        except aiohttp.ClientResponseError as e:
            logger.error("HTTP error {}: {}", e.status, e.message)
            raise
        except aiohttp.ClientError as e:
            logger.critical("Connection error: {}", str(e))
            raise
        except Exception as e:
            logger.exception("Unexpected error during request: {}", e)
            raise

    def _decode_images(self, response: Dict) -> List[bytes]:
        """Декодирование изображений из ответа"""
        if 'images' not in response and "image" not in response:
            logger.error("No images in response: {}", response)
            raise ValueError("Invalid API response format")

        images = response.get('images', [response.get('image')])
        return [base64.b64decode(img) for img in images if img is not None]

    def _b64_encode(self, data: bytes) -> str:
        """Кодирование в base64"""
        return base64.b64encode(data).decode('utf-8')

    def _validate_required_params(self, params: Dict, required: set) -> None:
        """Проверка обязательных параметров"""
        missing = required - params.keys()
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")

    def _sanitize_log_data(self, data: Dict) -> Dict:
        """Очистка данных для логирования"""
        return {k: v for k, v in data.items() if k not in ['init_images']}


async def save_images(images: List[bytes], save_dir: str = "output") -> List[str]:
    """Сохранение изображений в указанную директорию"""
    Path(save_dir).mkdir(exist_ok=True)
    paths = []
    
    for i, img_data in enumerate(images):
        filename = get_next_free_path(save_dir)
        with open(filename, "wb") as f:
            f.write(img_data)
        paths.append(filename)
        
        if HAS_PILLOW:
            with Image.open(BytesIO(img_data)) as img:
                logger.info(f"Saved image {i}: {img.format}, size: {img.size}px")
        else:
            logger.info(f"Saved image {i} as {filename} (size: {len(img_data)//1024} KB)")
    
    return paths


async def monitor_progress(sd_client: AsyncSDClient, interval: float = 1.0) -> None:
    """Мониторинг прогресса генерации с отображением в консоли"""
    last_valid_progress = 0.0
    attempts = 0
    
    while True:
        try:
            progress_data = await sd_client.get_progress()
            if not progress_data:
                attempts += 1
                if attempts > 3:
                    logger.error("Progress check failed multiple times")
                    break
                await asyncio.sleep(2)
                continue
            
            attempts = 0
            current = progress_data.get('progress', 0.0)
            eta = progress_data.get('eta_relative', 0.0)
            status = progress_data.get('textinfo', 'Unknown')
            
            if current > last_valid_progress:
                await _save_progress_image(progress_data)
                last_valid_progress = current

            if current >= 1.0 or (current == 0.0 and last_valid_progress >= 0.5):
                logger.info("Generation completed")
                break
                
            print(f"\rProgress: {current*100:.1f}% | ETA: {eta:.1f}s | Status: {status}", end="")
            
        except Exception as e:
            logger.error(f"Monitoring error: {str(e)}")
            break
            
        await asyncio.sleep(interval)


async def _save_progress_image(data: Dict) -> None:
    """Сохранение промежуточного изображения прогресса"""
    if not data.get('current_image'):
        return
        
    try:
        img_dir = Path("output/progress")
        img_dir.mkdir(exist_ok=True)
        
        img_data = base64.b64decode(data['current_image'])
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"progress_{timestamp}_{int(data['progress']*100):03d}.png"
        
        (img_dir / filename).write_bytes(img_data)
        logger.debug(f"Saved progress image: {filename}")
    except Exception as e:
        logger.warning(f"Failed to save progress image: {str(e)}")


async def test_image_generation() -> None:
    """Тест генерации изображений"""
    async with AsyncSDClient() as sd:
        images = await sd.txt2img(
            prompt="A futuristic cityscape at sunset, digital art, 4k",
            steps=25,
            width=768,
            height=512,
            cfg_scale=7.5,
            sampler_name="DPM++ 2M Karras"
        )
        await save_images(images)
        logger.success("Generated {} images", len(images))


async def main() -> None:
    """Основная функция"""
    logger.add("debug.log", rotation="1 MB")
    await test_image_generation()



if __name__ == "__main__":
    asyncio.run(main())