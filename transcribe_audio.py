import time
import whisperx
import torch
import numpy as np
from pathlib import Path
from resemblyzer import VoiceEncoder, preprocess_wav
from sklearn.cluster import AgglomerativeClustering
from call_analysis import get_speaker_roles
from loguru import logger

def process_audio_file(audio_path: Path, window_size: float = 3.0):
    try:
        wav = preprocess_wav(audio_path)
        sr = 16000

        seg_samples = int(window_size * sr)
        segments = [wav[i:i + seg_samples] for i in range(0, len(wav), seg_samples)]

        encoder = VoiceEncoder()
        embeddings = np.array([encoder.embed_utterance(seg) for seg in segments])

        clustering = AgglomerativeClustering(n_clusters=2)
        labels = clustering.fit_predict(embeddings)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "float32"
        model = whisperx.load_model("small", device=device, compute_type=compute_type)
        result = model.transcribe(str(audio_path))

        final_results = []
        for seg in result["segments"]:
            start_time = seg["start"]
            idx = min(int(start_time // window_size), len(labels) - 1)
            speaker_name = f"Speaker {labels[idx] + 1}"
            final_results.append({
                "start": start_time,
                "end": seg["end"],
                "speaker": speaker_name,
                "text": seg["text"].strip()
            })
        dialog_text_for_roles = "\n".join(
            [f"[{r['start']:.2f}s - {r['end']:.2f}s] {r['speaker']}: {r['text']}" for r in final_results])

        roles = get_speaker_roles(dialog_text_for_roles)

        for r in final_results:
            r["speaker"] = roles.get(r["speaker"], r["speaker"])

        processed_files = []
        output_folder = Path("transcribed_files")

        output_folder.mkdir(parents=True, exist_ok=True)
        output_path = output_folder / f"{audio_path.stem}_with_roles.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            for r in final_results:
                f.write(f"[{r['start']:.2f}s - {r['end']:.2f}s] {r['speaker']}: {r['text']}\n")

        processed_files.append(str(output_path))
        return processed_files
    except Exception as e:
        logger.error(f"Error: {e}")
        raise e

def yes_no_to_binary(value: str) -> int:
    if value.lower() in ["да", "так"]:
        return 1
    elif value.lower() in ["нет", "ні"]:
        return 0
    else:
        return 0