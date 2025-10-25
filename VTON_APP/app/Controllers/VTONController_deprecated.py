"""
DEPRECATED: This file contains the old VTONController implementation using Gemini AI.
This implementation has been replaced with a new Vertex AI-based implementation.

The old implementation used:
- Gemini 2.5 Flash Image model
- Custom system prompts for garment-only and cloths-on scenarios
- GenerateContentConfig with temperature, top_p, and top_k settings

The new implementation uses:
- Vertex AI Virtual Try-On API (virtual-try-on-preview-08-04)
- RecontextImageConfig for better control
- Simplified API that doesn't require the cloths_on flag

This file is kept for reference purposes only.
DO NOT USE THIS FILE - Use VTONController.py instead.
"""

from PIL import Image
from io import BytesIO
from google import genai
from google.genai.types import GenerateContentConfig
import socket
import requests
import logging

logger = logging.getLogger(__name__)


class VTONController:
    def __init__(self, api_key):
        self.api_key = api_key
        self.model_name = "gemini-2.5-flash-image"
        # print("api_key:", self.api_key)
        self.client = genai.Client(api_key=self.api_key)
        #         self.system_prompt = """
        # You are a professional AI virtual fashion stylist and photo editor.
        # Your job is to create realistic virtual try-on images by applying the given clothing image onto the person image.
        # Rules:
        # - Preserve the person's pose, body, face, hair, and background.
        # - The new clothing must fit naturally with realistic lighting and shadows.
        # - Avoid modifying identity, expression, or scene background.
        # - Ensure results are modest, natural, and photorealistic.
        # """

        # self.system_prompt = """Your task is to perform a virtual try-on. First, digitally remove the original clothing from the person in the first image. Then, take the *exact* clothing item from the second image and superimpose it onto the person, making it fit their body and pose perfectly. **Crucially, do not change, modify, or reinterpret the clothing item in any way.** The texture, pattern, color, and shape must be preserved perfectly from the source image. The final output must be only the edited image of the person wearing the new clothing."""

        # System prompt when cloths_on = False (clothing image shows just the garment)
        self.system_prompt_garment_only = """{
  "role": "system",
  "content": {
    "task": "You are an expert virtual try-on AI. You will be given a 'model image' and a 'garment image'. Your task is to create a new photorealistic image where the person from the 'model image' is wearing the clothing from the 'garment image'.",
    "rules": {
      "Complete Garment Replacement": "You MUST completely REMOVE and REPLACE all the clothing items worn by the person in the 'model image' with the new garment (or garments if there is a two or more than two piece suit in the source image). No part of the original clothing (e.g., collars, sleeves, patterns) should be visible in the final image. The new garment should not be similar to the previous garment the person was wearing. It shouldn't imitate the style of the previous garment. The new garment should look entirely like the person has changed clothes and is wearing the new garment.",
      "Preserve the Model": "The person's face, hair, body shape, and pose from the 'model image' MUST remain unchanged.",
      "Preserve the Background": "The entire background from the 'model image' MUST be preserved perfectly.",
      "Apply the Garment": "Realistically fit the new garment onto the person. It should adapt to their pose with natural folds, shadows, and lighting consistent with the original scene. The applied garment's design and dimensions should not change and should remain the same as in the source image."
    },
    "output": "Return ONLY the final, edited image. Do not include any text."
  }
}"""

        # System prompt when cloths_on = True (clothing image shows someone wearing the garment)
        self.system_prompt_cloths_on_model = """{
  "role": "system",
  "content": {
    "task": "You are an expert virtual try-on AI. You will be given two images: a 'target model image' and a 'reference image showing someone wearing a garment'. Your task is to create a new photorealistic image where the person from the 'target model image' is wearing the EXACT SAME clothing that the person in the 'reference image' is wearing.",
    "rules": {
      "Extract the Garment": "First, identify and extract the clothing/garment being worn by the person in the 'reference image'. Pay close attention to the garment's design, pattern, color, texture, and style details.",
      "Complete Garment Replacement": "You MUST completely REMOVE and REPLACE all the clothing items worn by the person in the 'target model image' with the extracted garment from the reference image. No part of the original clothing should be visible in the final image.",
      "Preserve the Target Model": "The person's face, hair, body shape, and pose from the 'target model image' MUST remain unchanged.",
      "Preserve the Background": "The entire background from the 'target model image' MUST be preserved perfectly.",
      "Apply the Extracted Garment": "Realistically fit the extracted garment onto the target person. It should adapt to their pose with natural folds, shadows, and lighting consistent with the target model's scene. The garment's design, pattern, color, and dimensions should remain identical to what was worn in the reference image."
    },
    "output": "Return ONLY the final, edited image. Do not include any text."
  }
}"""

        # Default user prompts for each flow
        self.default_prompt_garment_only = "Generate a realistic image of the person from the first image wearing the clothing from the second image. Ensure the clothing fits naturally on the person's body, maintaining the original pose, background, and lighting as much as possible. Do not alter the person's face, hair, or other features. Also do not alter the clothing in any way (design, dimensions etc.). The clothing should also be the same as in the source image."

        self.default_prompt_cloths_on_model = "Generate a realistic image of the person from the first image wearing the exact same clothing that the person in the second image is wearing. Extract the garment from the reference image and apply it to the target person. Ensure the clothing fits naturally on the target person's body, maintaining their original pose, background, and lighting. Do not alter the target person's face, hair, or other features. The clothing should be identical to what is worn in the reference image (same design, pattern, color, and dimensions)."

    #         """
    # Apply the clothing from the second image onto the person in the first image realistically.
    # Ensure the result looks natural, with proper fit and consistent lighting.
    # """

    def generate_virtual_tryon(self, person_image, clothing_image, instructions=None, cloths_on=False):
        """
        Generate virtual try-on image using Gemini AI

        Args:
            person_image: PIL Image object or file path
            clothing_image: PIL Image object or file path
            instructions: Optional custom instructions (string)
            cloths_on: Boolean flag indicating if clothing_image shows someone wearing the garment (True)
                     or just the garment alone (False). Default is False.

        Returns:
            PIL Image object of the generated result
        """
        try:
            # Load images if file paths are provided
            if isinstance(person_image, str):
                person_image = Image.open(person_image)
            if isinstance(clothing_image, str):
                clothing_image = Image.open(clothing_image)

            # Select appropriate prompts based on cloths_on flag
            if cloths_on:
                # Clothing image shows someone wearing the garment
                # System instruction should be plain text, not JSON
                system_prompt = """You are an expert virtual try-on AI. You will be given two images: a 'target model image' and a 'reference image showing someone wearing a garment'. Your task is to create a new photorealistic image where the person from the 'target model image' is wearing the EXACT SAME clothing that the person in the 'reference image' is wearing.

Rules:
1. Extract the Garment: First, identify and extract the clothing/garment being worn by the person in the 'reference image'. Pay close attention to the garment's design, pattern, color, texture, and style details.
2. Complete Garment Replacement: You MUST completely REMOVE and REPLACE all the clothing items worn by the person in the 'target model image' with the extracted garment from the reference image. No part of the original clothing should be visible in the final image.
3. Preserve the Target Model: The person's face, hair, body shape, and pose from the 'target model image' MUST remain unchanged.
4. Preserve the Background: The entire background from the 'target model image' MUST be preserved perfectly.
5. Apply the Extracted Garment: Realistically fit the extracted garment onto the target person. It should adapt to their pose with natural folds, shadows, and lighting consistent with the target model's scene. The garment's design, pattern, color, and dimensions should remain identical to what was worn in the reference image.

Output: Return ONLY the final, edited image. Do not include any text."""

                default_prompt = "Generate a realistic image of the person from the first image wearing the exact same clothing that the person in the second image is wearing. Extract the garment from the reference image and apply it to the target person. Ensure the clothing fits naturally on the target person's body, maintaining their original pose, background, and lighting. Do not alter the target person's face, hair, or other features. The clothing should be identical to what is worn in the reference image (same design, pattern, color, and dimensions)."
            else:
                # Clothing image shows just the garment
                system_prompt = """You are an expert virtual try-on AI. You will be given a 'model image' and a 'garment image'. Your task is to create a new photorealistic image where the person from the 'model image' is wearing the clothing from the 'garment image'.

Rules:
1. Complete Garment Replacement: You MUST completely REMOVE and REPLACE all the clothing items worn by the person in the 'model image' with the new garment (or garments if there is a two or more than two piece suit in the source image). No part of the original clothing (e.g., collars, sleeves, patterns) should be visible in the final image. The new garment should not be similar to the previous garment the person was wearing. It shouldn't imitate the style of the previous garment. The new garment should look entirely like the person has changed clothes and is wearing the new garment.
2. Preserve the Model: The person's face, hair, body shape, and pose from the 'model image' MUST remain unchanged.
3. Preserve the Background: The entire background from the 'model image' MUST be preserved perfectly.
4. Apply the Garment: Realistically fit the new garment onto the person. It should adapt to their pose with natural folds, shadows, and lighting consistent with the original scene. The applied garment's design and dimensions should not change and should remain the same as in the source image.

Output: Return ONLY the final, edited image. Do not include any text."""

                default_prompt = "Generate a realistic image of the person from the first image wearing the clothing from the second image. Ensure the clothing fits naturally on the person's body, maintaining the original pose, background, and lighting as much as possible. Do not alter the person's face, hair, or other features. Also do not alter the clothing in any way (design, dimensions etc.). The clothing should also be the same as in the source image."

            # Construct final prompt
            final_prompt = default_prompt
            if instructions and instructions.strip():
                final_prompt += "\nAlso, " + instructions.strip()

            # Log the request details
            logger.info(f"Processing VTON request with cloths_on={cloths_on}")
            logger.info(f"Prompt length: {len(final_prompt)}")

            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[final_prompt, person_image, clothing_image],
                config=GenerateContentConfig(
                    system_instruction=system_prompt,  # Changed from list to string
                    temperature=0.4,
                    top_p=0.95,
                    top_k=40,
                ),
            )

            # Log response details
            logger.info(f"Response received. Candidates: {len(response.candidates) if response.candidates else 0}")

            # Check if response has candidates
            if not response.candidates or len(response.candidates) == 0:
                # Log the full response for debugging
                logger.error(f"No candidates in response. Response: {response}")

                # Check for safety ratings
                if hasattr(response, "prompt_feedback"):
                    logger.error(f"Prompt feedback: {response.prompt_feedback}")
                    if hasattr(response.prompt_feedback, "block_reason"):
                        raise Exception(f"Request blocked by safety filters: {response.prompt_feedback.block_reason}")

                raise Exception("No image generated from API response. The request may have been blocked by safety filters or size limits.")

            # Extract generated image
            generated_image = None
            for candidate in response.candidates:
                if not hasattr(candidate, "content") or candidate.content is None:
                    logger.warning(f"Candidate has no content: {candidate}")
                    continue

                if not hasattr(candidate.content, "parts") or candidate.content.parts is None:
                    logger.warning(f"Candidate content has no parts: {candidate.content}")
                    continue

                for part in candidate.content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        image_data = part.inline_data.data
                        generated_image = Image.open(BytesIO(image_data))
                        break
                if generated_image:
                    break

            if not generated_image:
                raise Exception("No image data found in API response")

            return generated_image

        except socket.gaierror as e:
            # Network/DNS resolution error
            raise Exception(
                "Network connection error: Unable to reach Google GenAI API. " "Please check your internet connection and try again. " f"Details: {str(e)}"
            )
        except requests.exceptions.ConnectionError as e:
            # Connection error
            raise Exception(
                "Connection error: Unable to connect to Google GenAI API. " "Please check your internet connection or firewall settings. " f"Details: {str(e)}"
            )
        except requests.exceptions.Timeout as e:
            # Timeout error
            raise Exception("Request timeout: The API request took too long. " "Please try again later. " f"Details: {str(e)}")
        except Exception as e:
            # Handle other exceptions with more specific error message
            error_str = str(e).lower()
            if "getaddrinfo failed" in error_str or "11001" in error_str:
                raise Exception(
                    "Network connection error: Unable to resolve Google GenAI API hostname. "
                    "Please check your internet connection, DNS settings, or firewall configuration."
                )
            elif "api key" in error_str or "authentication" in error_str:
                raise Exception("API authentication error: Invalid or missing API key. " "Please check your GOOGLE_GENAI_API_KEY configuration.")
            else:
                raise Exception(f"Virtual try-on generation failed: {str(e)}")

    def save_result(self, image, output_path):
        """
        Save generated image to file

        Args:
            image: PIL Image object
            output_path: File path to save the image
        """
        image.save(output_path, format="PNG")
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
