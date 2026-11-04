import os
import platform
import subprocess
import uuid
from pathlib import Path
from dotenv import load_dotenv
from deepgram import DeepgramClient

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DOCTOR_AUDIO = BASE_DIR / "doctor_response.mp3"


def convert_text_to_doctor_audio(text, output_filepath=None):
    deepgram_api_key = os.environ.get("DEEPGRAM_API_KEY")
    if not deepgram_api_key:
        raise ValueError("DEEPGRAM_API_KEY is not set. Please add it to your .env file.")

    if output_filepath is None:
        # Use unique filename to prevent file lock conflicts on Windows
        output_filepath = BASE_DIR / f"doctor_response_{uuid.uuid4().hex[:8]}.mp3"
    else:
        output_filepath = Path(output_filepath)

    deepgram = DeepgramClient(api_key=deepgram_api_key)
    audio = deepgram.speak.v1.audio.generate(
        text=text,
        model=os.environ.get("DEEPGRAM_TTS_MODEL", "aura-2-thalia-en"),
        encoding="mp3",
    )

    with output_filepath.open("wb") as file:
        for chunk in audio:
            file.write(chunk)

    return output_filepath


def play_audio(audio_filepath):
    audio_filepath = str(audio_filepath)

    if platform.system() == "Darwin":
        subprocess.run(["afplay", audio_filepath], check=False)
    elif platform.system() == "Windows":
        os.startfile(audio_filepath)
    else:
        subprocess.run(["xdg-open", audio_filepath], check=False)


if __name__ == "__main__":
    test_text = "Hi, my name is AI Skin Specialist. I am here to assist you."
    print("Testing doctor voice synthesis...")
    output = convert_text_to_doctor_audio(test_text)
    print(f"Audio generated at: {output}")
