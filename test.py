import streamlit as st
from PIL import Image
from io import BytesIO

# Old SDK import replaced with new client-based SDK
from google import genai
from google.genai.types import GenerateContentConfig

# ----------------------------
# CONFIGURATION
# ----------------------------
st.set_page_config(page_title="Virtual Try-On", page_icon="👗", layout="centered")

# Your Gemini API key (replace if needed)
API_KEY = "AIzaSyC_--RMQDVbN103-aNVqqypOBxxo7ITyLc"
MODEL_NAME = "gemini-2.5-flash-image"

# Initialize client using the new SDK
client = genai.Client(api_key=API_KEY)

st.title("👗 AI Virtual Try-On")
st.write("Upload a person and clothing image — AI will realistically apply the outfit.")

# ----------------------------
# SIDEBAR INFO
# ----------------------------
with st.sidebar:
    st.header("🧾 Instructions")
    st.markdown(
        """
    1. Upload **person image** (target).  
    2. Upload **clothing image** (source).  
    3. Optionally, add your own description.  
    4. Click **Generate Virtual Try-On**.
    """
    )

# ----------------------------
# IMAGE UPLOAD
# ----------------------------
col1, col2 = st.columns(2)

with col1:
    person_file = st.file_uploader("👤 Upload Person Image", type=["jpg", "jpeg", "png"])
    if person_file:
        img_person = Image.open(person_file)
        st.image(img_person, caption="Person", use_container_width=True)

with col2:
    cloth_file = st.file_uploader("👕 Upload Clothing Image", type=["jpg", "jpeg", "png"])
    if cloth_file:
        img_cloth = Image.open(cloth_file)
        st.image(img_cloth, caption="Clothing", use_container_width=True)

# ----------------------------
# PROMPTS
# ----------------------------
system_prompt = """
You are a professional AI virtual fashion stylist and photo editor.
Your job is to create realistic virtual try-on images by applying the given clothing image onto the person image.
Rules:
- Preserve the person's pose, body, face, hair, and background.
- The new clothing must fit naturally with realistic lighting and shadows.
- Avoid modifying identity, expression, or scene background.
- Ensure results are modest, natural, and photorealistic.
"""

default_prompt = """
Apply the clothing from the second image onto the person in the first image realistically.
Ensure the result looks natural, with proper fit and consistent lighting.
"""

user_prompt = st.text_area("📝 Optional: Add Custom Instruction", placeholder="e.g., make the outfit slightly brighter, tuck in the shirt, etc.")

# Combine all prompts
final_prompt = default_prompt
if user_prompt.strip():
    final_prompt += "\nAlso, " + user_prompt.strip()

# ----------------------------
# GENERATE OUTPUT
# ----------------------------
if st.button("✨ Generate Virtual Try-On", use_container_width=True):
    if not (person_file and cloth_file):
        st.error("Please upload both the person and clothing images.")
        st.stop()

    try:
        with st.spinner("⏳ Generating realistic try-on... Please wait..."):

            # Use new client.models.generate_content API (multimodal: prompt + images)
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[final_prompt, img_person, img_cloth],
                config=GenerateContentConfig(system_instruction=[system_prompt]),
            )

            # ----------------------------
            # EXTRACT GENERATED IMAGE
            # ----------------------------
            generated_image = None
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        image_data = part.inline_data.data
                        generated_image = Image.open(BytesIO(image_data))
                        break
                if generated_image:
                    break

            # ----------------------------
            # DISPLAY RESULT
            # ----------------------------
            if generated_image:
                st.success("✅ Virtual try-on completed successfully!")
                st.image(generated_image, caption="Result", use_container_width=True)

                # Download button
                buf = BytesIO()
                generated_image.save(buf, format="PNG")
                st.download_button("⬇️ Download Result", data=buf.getvalue(), file_name="virtual_try_on_result.png", mime="image/png")
            else:
                st.error("❌ No image generated. Please check API key or model access.")
                st.text(response)

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
