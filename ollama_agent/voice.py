"""Speech-to-text input via microphone, using faster-whisper.

Deliberately lightweight: record until the user presses Enter, then run
Whisper on the captured audio. Both sounddevice and faster-whisper are
imported lazily so the rest of ola keeps working even without them.
"""

from __future__ import annotations

_MODEL_CACHE: dict[str, object] = {}


def _get_model(size: str):
    """Load (and cache) the Whisper model."""
    if size in _MODEL_CACHE:
        return _MODEL_CACHE[size]
    from faster_whisper import WhisperModel
    # CPU int8 quantization is a good default: fast enough on modern laptops
    # and keeps memory under 1GB even for the 'small' model.
    model = WhisperModel(size, device="cpu", compute_type="int8")
    _MODEL_CACHE[size] = model
    return model


def record_and_transcribe(
    language: str = "it",
    model_size: str = "medium",
    sample_rate: int = 16000,
) -> tuple[str, str | None]:
    """Record from the default mic until Enter, then transcribe.

    Returns (text, error). On success, error is None.
    """
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError:
        return "", (
            "sounddevice/numpy non installati. Installa con: "
            "pip install sounddevice numpy"
        )
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return "", (
            "faster-whisper non installato. Installa con: "
            "pip install faster-whisper"
        )

    frames: list = []

    def _callback(indata, _frames, _time, _status):
        frames.append(indata.copy())

    try:
        stream = sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            callback=_callback,
        )
    except Exception as e:
        return "", f"Impossibile aprire il microfono: {e}"

    with stream:
        try:
            input()  # block until Enter (or EOFError on Ctrl+D)
        except (EOFError, KeyboardInterrupt):
            pass

    if not frames:
        return "", None

    import numpy as np
    audio = np.concatenate(frames, axis=0).flatten().astype("float32")

    if audio.size < sample_rate // 4:  # <250ms — probably nothing useful
        return "", None

    try:
        model = _get_model(model_size)
    except Exception as e:
        return "", f"Errore caricamento modello Whisper '{model_size}': {e}"

    try:
        segments, _info = model.transcribe(
            audio,
            language=language,
            beam_size=5,
            vad_filter=True,
        )
        text = " ".join(s.text for s in segments).strip()
    except Exception as e:
        return "", f"Errore trascrizione: {e}"

    return text, None
