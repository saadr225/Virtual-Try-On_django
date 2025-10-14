from PIL import Image
from io import BytesIO
from google import genai
from google.genai.types import GenerateContentConfig


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
        self.system_prompt = """Your task is to perform a virtual try-on. First, digitally remove the original clothing from the person in the first image. Then, take the *exact* clothing item from the second image and superimpose it onto the person, making it fit their body and pose perfectly. **Crucially, do not change, modify, or reinterpret the clothing item in any way.** The texture, pattern, color, and shape must be preserved perfectly from the source image. The final output must be only the edited image of the person wearing the new clothing."""

        self.default_prompt = ""

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
                # final_prompt += "\nAlso, " + instructions.strip()
                final_prompt += instructions.strip()

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

        except Exception as e:
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
