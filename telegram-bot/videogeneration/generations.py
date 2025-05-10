from videogeneration.sdapi_cleared import AsyncSDClient, save_images
from loguru import logger
import asyncio

from typing import List
import asyncio
from pathlib import Path
from loguru import logger

def generate_photo(prompt: str) -> str:
    """Генерирует изображение по текстовому описанию и возвращает путь к файлу.
    
    Args:
        prompt: Текстовое описание для генерации изображения
        
    Returns:
        str: Абсолютный путь к сгенерированному изображению
    """
    async def _async_generate() -> str:
        async with AsyncSDClient() as sd:
            await sd.initialize()
            
            # Параметры по умолчанию
            params = {
                "prompt": prompt,
                "negative_prompt": "low quality, deformed, blurry",
                "steps": 25,
                "width": 512,
                "height": 768,
                "cfg_scale": 7.5,
                "sampler_name": "DPM++ 2M Karras",
                "seed": -1,
                "n_iter": 1,
                "batch_size": 1
            }
            
            # Выбираем первый доступный сэмплер, если указанный недоступен
            if not any(s["name"] == params["sampler_name"] for s in sd.samplers):
                params["sampler_name"] = sd.samplers[0]["name"]
                logger.warning("Using fallback sampler: {}", params["sampler_name"])
            
            images = await sd.txt2img(**params)
            paths = await save_images(images, "output/generated")
            return paths[0] if paths else ""

    try:
        return asyncio.run(_async_generate())
    except Exception as e:
        logger.error("Generation failed: {}", str(e))
        return ""

def generate_sequential_variations(
    prompt: str,
    initial_photo: str,
    iterations: int = 5,
    denoising_strength: float = 0.4,
    delay_between_steps: float = 1.0
) -> List[str]:
    """
    Генерирует последовательные вариации изображения через цепочку img2img преобразований.
    
    Args:
        prompt: Текстовое описание для генерации
        initial_photo: Путь к начальному изображению
        iterations: Количество последовательных генераций
        denoising_strength: Сила влияния на каждое преобразование (0.3-0.6)
        delay_between_steps: Задержка между шагами в секундах
        
    Returns:
        List[str]: Список путей к сгенерированным изображениям в порядке генерации
    """
    async def _async_generate() -> List[str]:
        async with AsyncSDClient() as sd:
            await sd.initialize()
            
            # Загрузка исходного изображения
            try:
                with open(initial_photo, "rb") as f:
                    current_image = f.read()
            except Exception as e:
                logger.error(f"Image loading failed: {str(e)}")
                return []

            generated_paths = []
            total_steps = iterations
            
            # Базовые параметры генерации
            base_params = {
                "prompt": prompt,
                "negative_prompt": "deformed, blurry, low quality, artifacts",
                "steps": 20,
                "width": 512,
                "height": 768,
                "cfg_scale": 7,
                "sampler_name": "Euler a",
                "seed": -1,
                "resize_mode": 1,
                "denoising_strength": max(0.3, min(denoising_strength, 0.6)),
                "restore_faces": True
            }

            # Цикл последовательной генерации
            for step in range(total_steps):
                try:
                    # Генерация следующего изображения
                    images = await sd.img2img(
                        init_images=[current_image],
                        **base_params
                    )
                    
                    if not images:
                        logger.warning(f"Empty response at step {step+1}")
                        continue
                        
                    # Сохранение и обновление текущего изображения
                    new_paths = await save_images(images, "output/sequential")
                    if new_paths:
                        current_image = Path(new_paths[0]).read_bytes()
                        generated_paths.extend(new_paths)
                        logger.info(f"Generated step {step+1}/{total_steps}")
                    
                    # Задержка между шагами
                    await asyncio.sleep(delay_between_steps)
                    
                except Exception as e:
                    logger.error(f"Step {step+1} failed: {str(e)}")
                    break

            return generated_paths

    try:
        return asyncio.run(_async_generate())
    except Exception as e:
        logger.error(f"Generation process failed: {str(e)}")
        return []