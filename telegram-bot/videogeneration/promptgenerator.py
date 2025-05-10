import random
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from videogeneration.config import GIGACHAT_CREDENTIALS, PROMPT_TYPE, CA_BUNDLE_FILE
import os
import re

from loguru import logger

class PromptGenerator:
    def __init__(self):
        logger.info("Initializing Simple PromptGenerator")
        self.objects = [
            'cyberpunk cat', 'vibrant galaxy', 'steampunk owl', 
            'surreal landscape', 'anime warrior', 'bioorganic structure',
            'futuristic cityscape', 'psychedelic unicorn', 'robotic samurai',
            'crystal cavern', 'apocalyptic wasteland', 'enchanted forest'
        ]
        
        self.styles = [
            'digital painting', 'concept art', 'octane render', 
            'unreal engine', 'cyberpunk 2077 style', 'synthwave',
            'low poly', 'isometric', 'glitch art', 'luminous',
            'hyperrealistic', 'watercolor', 'ink illustration',
            'retro futurism', '3D render'
        ]
        
        self.colors = [
            'vivid neon', 'monochrome', 'pastel gradient', 
            'electric tones', 'metallic sheen', 'dark contrast',
            'warm sunset', 'cyber violet', 'holographic',
            'bioluminescent', 'gold accents', 'chrome'
        ]
        
        self.locations = [
            'floating islands', 'neon metropolis', 'underwater ruins',
            'cyberspace matrix', 'alien marketplace', 'crystal desert',
            'volcanic forge', 'nebula core', 'haunted cathedral',
            'quantum realm', 'neural network'
        ]
        
        self.details = [
            'intricate details', 'dynamic lighting', 'volumetric fog',
            'particle effects', 'cinematic composition', '4k resolution',
            'hyperdetailed textures', 'ray tracing', 'motion blur',
            'depth of field', 'symmetrical patterns'
        ]

    def generate_prompt(self):
        logger.info("Starting simple prompt generation")
        components = [
            f"A {random.choice(self.objects)} in {random.choice(self.locations)}, "
            f"{random.choice(self.styles)}, {random.choice(self.colors)} palette, "
            f"{random.choice(self.details)}, {random.choice(self.details)}"
        ]
        
        # Добавляем модификаторы для уникальности
        modifiers = [
            'trending on artstation', 'ultra HD', '8k resolution',
            'unreal engine 5', 'nvidia ray tracing', 'epic composition'
        ]
        
        prompt = " ".join(components) + f", {random.choice(modifiers)}"
        result = prompt[:400]
        if len(prompt) > 400:
            logger.warning(f"Prompt truncated from {len(prompt)} to 400 characters")

        logger.debug(f"Generated simple prompt: {result}")
        return result  # Обрезаем до допустимой длины



class GigaChatPromptGenerator:
    def __init__(self):
        logger.info("Initializing GigaChatPromptGenerator")
        self.credentials = GIGACHAT_CREDENTIALS
        self.ca_bundle = CA_BUNDLE_FILE
        self.tech_modifiers = [
            "with adaptive nano-textiles", "featuring quantum dot illumination",
            "using photonic lattice structures", "with biomimetic surface patterns",
            "incorporating ferrofluid dynamics", "with chameleon pigment technology"
        ]

    def generate_prompt(self, base_theme=None):
        logger.info("Starting GigaChat prompt generation")
        if not base_theme:
            base_theme = self._generate_base_concept()
            logger.debug(f"Generated base concept: {base_theme}")
            
        with GigaChat(
            credentials=self.credentials,
            ca_bundle_file=self.ca_bundle,
            verify_ssl_certs=True
        ) as model:
            logger.debug("Creating GigaChat session")
            chat = Chat(
                messages=[
                    Messages(
                        role=MessagesRole.SYSTEM,
                        content=self._construct_system_prompt()
                    ),
                    Messages(
                        role=MessagesRole.USER,
                        content=f"Concept: {base_theme}"
                    )
                ],
                temperature=0.75,
                max_tokens=450
            )
            
            try:
                logger.info("Sending request to GigaChat API")
                response = model.chat(chat)
                logger.success("Successfully generated prompt with GigaChat")
                logger.debug(f"Raw GigaChat response: {response.choices[0].message.content}")
                return self._clean_prompt(response.choices[0].message.content)
            except Exception as e:
                logger.error(f"GigaChat API error: {str(e)}")
                fallback = self._generate_fallback_prompt(base_theme)
                logger.warning(f"Using fallback prompt: {fallback}")
                return fallback

    def _construct_system_prompt(self):
        logger.debug("Constructing system prompt")
        return """Generate a SINGLE cohesive Stable Diffusion prompt in English (200-400 characters) describing futuristic scenes for 2025. 
Requirements:
- Single continuous text without sections/bullets
- Include: environment, tech details, materials, lighting
- Focus on visual adjectives
- Style: photorealistic/sci-fi art
- No markdown/titles/separators

Example: "A sprawling underground tech-bazaar in 2025 Neo-Moscow, where glowing nano-fabric stalls illuminate crumbling Soviet-era architecture, holographic fashion shows project onto smoke-filled air, cyborg merchants display liquid-metal garments that ripple like mercury, neon lasers slice through industrial fog, 8k ultra-detailed with cinematic cyberpunk lighting, depth of field, trending on ArtStation"."""

    def _generate_base_concept(self):
        logger.debug("Generating base concept")
        locations = [
            "abandoned quantum server farm", "floating arcology district",
            "cryo-preserved fashion vault", "neon-drenched tech slums",
            "underground bio-hacker den", "derelict space elevator terminal"
        ]
        return f"{random.choice(locations)} {random.choice(self.tech_modifiers)}"

    def _clean_prompt(self, text):
        logger.debug("Cleaning generated prompt")
        cleaned = re.sub(r'\*\*|#|[-•]|\[|\]|{:|}', '', text)
        cleaned = ' '.join(cleaned.split('\n'))
        result = cleaned.strip()[:400].rstrip(',. ')
        logger.debug(f"Cleaned prompt: {result}")
        return result

    def _generate_fallback_prompt(self, concept):
        logger.warning("Generating fallback prompt")
        elements = [
            "A dystopian fashion hub in 2025 where",
            "neon-lit", "holographic", "biomechanical", "nano-enhanced",
            "garments", "interact with", "quantum computing nodes",
            "projected onto", "crumbling concrete structures",
            "amidst", "floating AR advertisements",
            "cybernetic", "models with", "glowing circuitry",
            "under", "pulsing UV arrays",
            "rendered in", "hyper-realistic 8k detail",
            "with", "volumetric fog effects",
            "and", "cinematic depth of field",
            "trending on ArtStation"
        ]
        return ' '.join(elements)[:400]
    
generators = {
    "SIMPLE": PromptGenerator(),
    "GIGACHAT": GigaChatPromptGenerator()
}
    
def generate_prompt():
    logger.info(f"Using {PROMPT_TYPE} prompt generator")
    result = generators[PROMPT_TYPE].generate_prompt()
    logger.debug(f"Final generated prompt: {result}")
    return result

    
if __name__ == "__main__":
    logger.info("Starting prompt generator test")
    generator = GigaChatPromptGenerator()
    test_prompt = generator.generate_prompt()
    logger.success(f"Test prompt generated: {test_prompt}")

    production_prompt = generate_prompt()
    logger.info(f"Production prompt result: {production_prompt}")