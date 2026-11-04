
import logging
import os
import time
from io import BytesIO
from pathlib import Path
from collections import deque

import numpy as np
import sounddevice as sd
import speech_recognition as sr

from dotenv import load_dotenv
from groq import Groq
from pydub import AudioSegment


# --------------------------------------------------
# Logging
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# --------------------------------------------------
# Configure FFmpeg
# --------------------------------------------------

# Uncomment these lines if FFmpeg is not available in PATH.

# AudioSegment.converter = r"C:\ffmpeg\bin\ffmpeg.exe"
# AudioSegment.ffprobe = r"C:\ffmpeg\bin\ffprobe.exe"


# --------------------------------------------------
# Step 1: Record audio using SoundDevice
# --------------------------------------------------

def record_audio(
    file_path,
    timeout=20,
    phrase_time_limit=10,
    silence_duration=0.8,
    calibration_duration=1.0
):
    """
    Record microphone audio using SoundDevice.

    No PyAudio required.

    Waits for speech, records until silence is detected
    or phrase_time_limit is reached, and saves MP3 audio.
    """

    sample_rate = None
    blocksize = 1024

    logging.info("Opening microphone...")

    try:

        # Get default microphone information
        device_info = sd.query_devices(kind="input")

        sample_rate = int(device_info["default_samplerate"])

        logging.info(
            f"Using microphone sample rate: {sample_rate} Hz"
        )

        # Calculate audio volume (RMS)
        def calculate_rms(audio_chunk):
            audio_float = audio_chunk.astype(np.float32)

            return float(
                np.sqrt(np.mean(audio_float ** 2))
            )

        recorded_frames = []

        # Keep a small amount of audio before speech starts
        pre_roll = deque(maxlen=3)

        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            blocksize=blocksize
        ) as stream:

            # ------------------------------------------
            # Ambient noise calibration
            # ------------------------------------------

            logging.info("Adjusting for ambient noise...")

            calibration_blocks = max(
                1,
                int(
                    sample_rate * calibration_duration / blocksize
                )
            )

            noise_levels = []

            for _ in range(calibration_blocks):

                chunk, overflowed = stream.read(blocksize)

                noise_levels.append(
                    calculate_rms(chunk)
                )

            ambient_noise = float(
                np.median(noise_levels)
            )

            # Set speech detection threshold
            energy_threshold = max(
                250.0,
                ambient_noise * 2.5
            )

            logging.info(
                f"Speech detection threshold: {energy_threshold:.2f}"
            )

            logging.info("Start speaking now...")

            start_deadline = time.monotonic() + timeout

            speech_started_at = None
            silence_started_at = None

            # ------------------------------------------
            # Record speech
            # ------------------------------------------

            while True:

                audio_chunk, overflowed = stream.read(
                    blocksize
                )

                current_time = time.monotonic()

                volume = calculate_rms(audio_chunk)

                # Wait for the user to start speaking
                if speech_started_at is None:

                    pre_roll.append(
                        audio_chunk.copy()
                    )

                    if volume >= energy_threshold:

                        speech_started_at = current_time

                        recorded_frames.extend(
                            list(pre_roll)
                        )

                        logging.info(
                            "Speech detected. Recording..."
                        )

                    elif current_time >= start_deadline:

                        raise sr.WaitTimeoutError()

                else:

                    recorded_frames.append(
                        audio_chunk.copy()
                    )

                    # Detect silence after speech begins
                    if volume < energy_threshold:

                        if silence_started_at is None:

                            silence_started_at = current_time

                        elif (
                            current_time - silence_started_at
                            >= silence_duration
                        ):

                            logging.info(
                                "Silence detected. Stopping recording."
                            )

                            break

                    else:

                        silence_started_at = None

                    # Maximum recording duration
                    if (
                        current_time - speech_started_at
                        >= phrase_time_limit
                    ):

                        logging.info(
                            "Maximum recording duration reached."
                        )

                        break

        # ------------------------------------------
        # Convert recorded frames into audio bytes
        # ------------------------------------------

        if not recorded_frames:

            logging.warning("No audio was recorded.")

            return None

        audio_array = np.concatenate(
            recorded_frames,
            axis=0
        )

        audio_data = sr.AudioData(
            audio_array.tobytes(),
            sample_rate,
            2
        )

        # ------------------------------------------
        # Convert WAV -> MP3
        # ------------------------------------------

        wav_data = audio_data.get_wav_data()

        audio_segment = AudioSegment.from_wav(
            BytesIO(wav_data)
        )

        output_path = Path(file_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        audio_segment.export(
            output_path,
            format="mp3",
            bitrate="128k"
        )

        logging.info(
            f"Audio saved to: {output_path.resolve()}"
        )

        return str(output_path)

    except sr.WaitTimeoutError:

        logging.error(
            "No speech detected within the timeout period."
        )

        return None

    except sd.PortAudioError as e:

        logging.error(
            f"Microphone or PortAudio error: {e}"
        )

        return None

    except Exception:

        logging.exception(
            "Recording failed."
        )

        return None


# --------------------------------------------------
# Step 2: Convert audio to text using Groq
# --------------------------------------------------

def transcribe_patient_voice(audio_filepath):
    api_key = os.getenv("GROQ_API_KEY") or GROQ_API_KEY
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found. "
            "Add GROQ_API_KEY=your_key_here to your .env file."
        )

    client = Groq(
        api_key=api_key
    )

    audio_path = Path(audio_filepath)

    if not audio_path.exists():

        raise FileNotFoundError(
            f"Audio file not found: {audio_path}"
        )

    logging.info("Sending audio to Groq...")

    with open(audio_path, "rb") as audio_file:

        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model=os.getenv(
                "WHISPER_MODEL",
                "whisper-large-v3"
            ),
            response_format="text"
        )

    if hasattr(transcription, "text"):
        return transcription.text.strip()
    return str(transcription).strip()


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    audio_filepath = BASE_DIR / "patient_voice_test.mp3"

    recorded_file = record_audio(
        audio_filepath,
        timeout=20,
        phrase_time_limit=10
    )

    if recorded_file:

        transcript = transcribe_patient_voice(
            recorded_file
        )

        print("\n" + "=" * 60)
        print("PATIENT TRANSCRIPTION")
        print("=" * 60)

        print(transcript)

        print("=" * 60)

    else:

        logging.warning(
            "Recording unsuccessful. Transcription skipped."
        )
