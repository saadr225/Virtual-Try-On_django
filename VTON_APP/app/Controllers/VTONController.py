from PIL import Image
from io import BytesIO
from google import genai
from google.genai.types import GenerateContentConfig
import socket
import requests


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

        self.system_prompt = """{
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

        self.default_prompt = "Generate a realistic image of the person from the first image wearing the clothing from the second image. Ensure the clothing fits naturally on the person's body, maintaining the original pose, background, and lighting as much as possible. Do not alter the person's face, hair, or other features. Also do not alter the clothing in any way (design, dimensions etc.). The clothing should also be the same as in the source image."

    #         """
    # Apply the clothing from the second image onto the person in the first image realistically.
    # Ensure the result looks natural, with proper fit and consistent lighting.
    # """

    def generate_virtual_tryon(self, person_image, clothing_image, instructions=None):
        """
        Generate virtual try-on image using Gemini AI

        Args:
            person_image: PIL Image object or file path
            clothing_image: PIL Image object or file path
            instructions: Optional custom instructions (string)

        Returns:
            PIL Image object of the generated result
        """
        try:
            # Load images if file paths are provided
            if isinstance(person_image, str):
                person_image = Image.open(person_image)
            if isinstance(clothing_image, str):
                clothing_image = Image.open(clothing_image)

            # Construct final prompt
            final_prompt = self.default_prompt
            if instructions and instructions.strip():
                final_prompt += "\nAlso, " + instructions.strip()
                # final_prompt += instructions.strip()

            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[final_prompt, person_image, clothing_image],
                config=GenerateContentConfig(system_instruction=[self.system_prompt]),
            )

            # Extract generated image
            generated_image = None
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        image_data = part.inline_data.data
                        generated_image = Image.open(BytesIO(image_data))
                        break
                if generated_image:
                    break

            if not generated_image:
                raise Exception("No image generated from API response")

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
