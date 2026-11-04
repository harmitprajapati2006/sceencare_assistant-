import base64
import io
import mimetypes
import os
import subprocess
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image

load_dotenv()


def prepare_image_for_llm(filepath, max_dimension=1024, quality=85):
    """
    Downsamples and compresses images to avoid HTTP 413 (Payload Too Large) errors
    while preserving high visual clarity for dermatological analysis.
    """
    with Image.open(filepath) as img:
        # Convert RGBA / P / Grayscale to RGB for clean JPEG compression
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Downsample proportionally if image is larger than max_dimension
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return encoded, "image/jpeg"


def extract_frame_from_video(video_filepath):
    """
    Extracts a representative frame from a video using ffmpeg.
    Returns the path to a temporary JPEG frame.
    """
    temp_frame = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    temp_frame.close()
    out_path = temp_frame.name

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", "00:00:00.500",
            "-i", str(video_filepath),
            "-vframes", "1",
            "-q:v", "2",
            out_path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path
    except Exception as e:
        print(f"Warning: ffmpeg frame extraction failed: {e}")

    return None


def clean_doctor_text(text):
    """
    Removes markdown asterisks, hashes, and formatting so the text
    reads naturally through Text-To-Speech.
    """
    if not text:
        return ""
    cleaned = text.replace("**", "").replace("*", "").replace("#", "").replace("`", "")
    return cleaned.strip()


def brain_of_the_doctor(patient_text, image_filepath=None, video_filepath=None):
    """
    Analyzes patient symptoms and visuals (image or video).
    Supports Groq Vision (e.g. qwen/qwen3.8-27b) and MiniMax (Anthropic endpoint).
    """
    groq_api_key = os.environ.get("GROQ_API_KEY")
    minimax_api_key = os.environ.get("MINIMAX_API_KEY")

    if not groq_api_key and not minimax_api_key:
        raise ValueError(
            "Neither GROQ_API_KEY nor MINIMAX_API_KEY was found in environment. "
            "Please check your .env file."
        )

    patient_description = (patient_text or "").strip()
    if not patient_description:
        patient_description = "The patient has not provided a spoken description, but has submitted visual media for assessment."

    prompt = (
        "You are an empathetic, confident medical doctor specializing in dermatology and skin care. "
        "Review the patient's concern and the provided visual examination. "
        "Limit your entire response to two or three clear, reassuring sentences maximum. "
        "Provide professional guidance and recommendations on next steps. "
        "Do not use markdown, asterisks, bullet points, or special characters because your response will be read aloud."
        f"\n\nPatient complaint: {patient_description}"
    )

    extracted_temp_frame = None
    target_image_path = None

    if image_filepath and os.path.exists(image_filepath):
        target_image_path = image_filepath
    elif video_filepath and os.path.exists(video_filepath):
        extracted_temp_frame = extract_frame_from_video(video_filepath)
        if extracted_temp_frame:
            target_image_path = extracted_temp_frame

    # Use Groq if available (default when GROQ_API_KEY is configured in .env)
    use_groq = bool(groq_api_key) and (not minimax_api_key or os.environ.get("VISION_PROVIDER") == "groq")

    try:
        if use_groq:
            from groq import Groq

            client = Groq(api_key=groq_api_key)
            model = os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b")

            user_content = [{"type": "text", "text": prompt}]

            if target_image_path:
                encoded_image, mime_type = prepare_image_for_llm(target_image_path)
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{encoded_image}"
                    },
                })

            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": user_content}],
                max_tokens=600,
            )
            raw_text = response.choices[0].message.content

        else:
            # MiniMax Anthropic-compatible client
            import anthropic

            client = anthropic.Anthropic(
                api_key=minimax_api_key,
                base_url=os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/anthropic"),
            )
            model = os.environ.get("MINIMAX_MODEL", "MiniMax-M3")

            content_items = []
            if target_image_path:
                encoded_image, mime_type = prepare_image_for_llm(target_image_path)
                content_items.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": encoded_image,
                    },
                })
            elif video_filepath and os.path.exists(video_filepath):
                with open(video_filepath, "rb") as f:
                    v_b64 = base64.b64encode(f.read()).decode("utf-8")
                content_items.append({
                    "type": "video",
                    "source": {
                        "type": "base64",
                        "media_type": "video/mp4",
                        "data": v_b64,
                    },
                })

            content_items.append({"type": "text", "text": prompt})

            response = client.messages.create(
                model=model,
                max_tokens=600,
                messages=[{"role": "user", "content": content_items}],
            )
            raw_text = response.content[0].text

        return clean_doctor_text(raw_text)

    finally:
        if extracted_temp_frame and os.path.exists(extracted_temp_frame):
            try:
                os.remove(extracted_temp_frame)
            except OSError:
                pass
