import base64
import mimetypes
from pathlib import Path
from openai import OpenAI
import io
from PIL import Image

def encode_image_to_data_uri(image_path: str | Path) -> str:
    """Reads a local image file and converts it to a base64 Data URI."""
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found at: {path}")

    # Determine MIME type (defaults to image/jpeg if unknown)
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type:
        mime_type = "image/jpeg"

    with open(path, "rb") as f:
        base64_encoded = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{base64_encoded}"


def encode_png_safely(image_path: str) -> str:
    with Image.open(image_path) as img:
        # If PNG has alpha channel or palette, composite onto a white background
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
            background = Image.new("RGBA", img.size, (255, 255, 255, 255))
            alpha_composite = Image.alpha_composite(background, img)
            rgb_img = alpha_composite.convert("RGB")
        else:
            rgb_img = img.convert("RGB")

        # Save as clean JPEG or clean PNG into a buffer
        buffered = io.BytesIO()
        rgb_img.save(buffered, format="JPEG", quality=95)
        encoded_string = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return f"data:image/jpeg;base64,{encoded_string}"


def test_vllm_vision(
    image_path: str,
    prompt: str = "Describe what you see in this image in detail.",
    model: str = "gemma4:20b",
    base_url: str = "http://localhost:8000/v1",
    api_key: str = "EMPTY",
):
    # Initialize OpenAI client pointing to your vLLM server
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    image_data_uri = encode_image_to_data_uri(image_path)

    print(f"Sending request to {base_url} (model: {model})...\n")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_uri,
                        },
                    },
                ],
            }
        ],
        max_tokens=512,
        temperature=0.2,
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    # Update with your test image path and model name
    TEST_IMAGE = "path/to/your/image.png"
    MODEL_NAME = "gemma4:20b"
    VLLM_URL = "http://localhost:8000/v1"

    result = test_vllm_vision(
        image_path=TEST_IMAGE,
        prompt="Extract any text visible in this image, or describe the main subject.",
        model=MODEL_NAME,
        base_url=VLLM_URL,
    )

    print("--- Model Response ---")
    print(result)
