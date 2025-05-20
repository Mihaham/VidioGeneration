from videogeneration.promptgenerator import generate_prompt
from videogeneration.generations import generate_photo, generate_sequential_variations
from videogeneration.firstpage import generate_first_page
from videogeneration.sound_generation import generate_audio_with_salut
from videogeneration.video_maker import compile_video
from loguru import logger

def generate_video():
    prompt = generate_prompt()

    photo = generate_photo(prompt=prompt)

    next_photos = generate_sequential_variations(prompt = prompt,
                                                 initial_photo=photo,
                                                 iterations=240)
    first_page, title = generate_first_page(prompt = prompt,
                                     initial_photo = photo)
    
    all_photos = [photo, *next_photos]
    
    audio_path, description = generate_audio_with_salut(prompt=prompt)
    video = compile_video(first_page=first_page, photos=all_photos, audio=audio_path)

    return video, [first_page, *all_photos], title, description

if __name__ == "__main__":
    for i in range(1):
        #try:
            generate_first_page("A enchanted forest in cyberspace matrix, octane re", r"B:\\Generation videos\\telegram-bot\\output\\generated\\image_0.png")
        #except Exception as e:
        #    logger.critical(f"{e}")
