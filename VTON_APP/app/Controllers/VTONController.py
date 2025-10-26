"""
VTONController - Virtual Try-On Controller using Vertex AI

This implementation uses:
- Vertex AI Virtual Try-On API (virtual-try-on-preview-08-04)
- RecontextImageConfig for fine-grained control
- Simplified API that works with both garment-only and cloths-on scenarios automatically

The API intelligently handles:
- Garment images (clothing item alone)
- Reference images (someone wearing the garment)
"""

from PIL import Image
from io import BytesIO
from google import genai
from google.genai.types import RecontextImageSource, ProductImage, Image as GenAIImage, RecontextImageConfig
import os
import logging
import tempfile

logger = logging.getLogger(__name__)


class VTONController:
    def __init__(self, api_key):
        """
        Initialize the VTON Controller with Vertex AI credentials

        Args:
            api_key: Google GenAI API key for authentication
        """
        self.api_key = api_key
        self.model_name = "virtual-try-on-preview-08-04"

        # Set up Vertex AI environment variables
        # os.environ["GOOGLE_CLOUD_PROJECT"] = "gen-lang-client-0870725395"
        # os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

        # Initialize the GenAI client
        self.client = genai.Client(api_key=self.api_key)

        # Default configuration for the Virtual Try-On API
        self.default_config = RecontextImageConfig(
            number_of_images=1,
            add_watermark=False,
            person_generation="allow_all",
            safety_filter_level="block_only_high",
            seed=42,
            enhance_prompt=True,
        )

        logger.info(f"VTONController initialized with model: {self.model_name}")

    def generate_virtual_tryon(self, person_image_path, clothing_image_path, instructions=None, cloths_on=False):
        """
        Generate virtual try-on image using Vertex AI Virtual Try-On API

        Args:
            person_image_path:  file path of the person
            clothing_image_path: file path of the clothing/garment
            instructions: Optional custom instructions (DEPRECATED - not used by Vertex AI API)
            cloths_on: DEPRECATED - The Vertex AI API automatically handles both scenarios

        Returns:
            PIL Image object of the generated result
        """
        try:
            # Log deprecation warning if cloths_on is explicitly set
            if cloths_on:
                logger.warning(
                    "The 'cloths_on' parameter is deprecated. "
                    "Vertex AI Virtual Try-On API automatically handles both garment-only "
                    "and cloths-on scenarios intelligently."
                )

            # Log deprecation warning if instructions are provided
            if instructions and instructions.strip():
                logger.warning(
                    "The 'instructions' parameter is deprecated. "
                    "Vertex AI Virtual Try-On API does not support custom instructions. "
                    "The API uses its own optimized prompting internally."
                )

            logger.info(f"Processing VTON request using {self.model_name}")

            # Call Vertex AI Virtual Try-On API
            response = self.client.models.recontext_image(
                model=self.model_name,
                source=RecontextImageSource(
                    person_image=GenAIImage.from_file(location=person_image_path),
                    product_images=[ProductImage(product_image=GenAIImage.from_file(location=clothing_image_path))],
                ),
                config=self.default_config,
            )

            # Log response details
            num_images = len(response.generated_images) if response.generated_images else 0
            logger.info(f"Response received. Generated images: {num_images}")

            if not response.generated_images or len(response.generated_images) == 0:
                raise Exception("No image generated from API response. The request may have failed.")

            # Get the first (and only) generated image
            generated_image_data = response.generated_images[0]

            # Convert from GenAI Image to PIL Image
            image_bytes = generated_image_data.image.image_bytes
            generated_image = Image.open(BytesIO(image_bytes))

            logger.info(f"Successfully generated virtual try-on image ({len(image_bytes)} bytes)")

            return generated_image

        except Exception as e:
            # Handle various error scenarios
            error_str = str(e).lower()

            if "api key" in error_str or "authentication" in error_str or "unauthorized" in error_str:
                raise Exception("API authentication error: Invalid or missing API key. " "Please check your VERTEX_AI_API_KEY configuration.")
            elif "quota" in error_str or "rate limit" in error_str:
                raise Exception("API quota exceeded: You have reached your API usage limit. " "Please check your Google Cloud quota and billing settings.")
            elif "safety" in error_str or "blocked" in error_str:
                raise Exception(
                    "Request blocked by safety filters: The image content may have been flagged. " "Please ensure the images comply with Google's usage policies."
                )
            elif "timeout" in error_str:
                raise Exception("Request timeout: The API request took too long. " "Please try again later.")
            elif "network" in error_str or "connection" in error_str:
                raise Exception("Network connection error: Unable to reach Vertex AI API. " "Please check your internet connection and try again.")
            else:
                # Check for PIL image identification errors (often due to safety blocks or invalid API responses)
                if "cannot identify image file" in str(e).lower():
                    logger.warning(f"Image identification failed - likely due to safety filters or invalid API response. Error: {str(e)}")
                    raise Exception(
                        "Unable to process the provided images. This may be due to content restrictions or image quality issues. "
                        "Please try using different images that comply with usage guidelines."
                    )
                else:
                    logger.error(f"Virtual try-on generation failed: {str(e)}")
                    raise Exception(f"Virtual try-on generation failed: {str(e)}")

    def save_result(self, image, output_path):
        """
        Save generated image to file

        Args:
            image: PIL Image object
            output_path: File path to save the image

        Returns:
            str: Path to the saved image
        """
        image.save(output_path, format="PNG")
        logger.info(f"Saved result image to: {output_path}")
        return output_path

    def get_image_bytes(self, image):
        """
        Convert PIL Image to bytes for download/response

        Args:
            image: PIL Image object

        Returns:
            BytesIO object containing image data
        """
        buf = BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return buf
