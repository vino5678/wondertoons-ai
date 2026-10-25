"""Optional, entirely local narration and generated audio for Windows exports."""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import wave
from pathlib import Path


class AudioGenerationError(Exception):
    """A local speech or soundtrack component could not be produced."""


_SPEECH_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Speech
    $encodedPayload = [Console]::In.ReadToEnd().Trim()
    $payloadJson = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($encodedPayload))
    $payload = $payloadJson | ConvertFrom-Json
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $voice = $synth.GetInstalledVoices() |
        Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name.StartsWith(
            [string]$payload.language, [System.StringComparison]::OrdinalIgnoreCase) } |
        Select-Object -First 1
    if ($null -eq $voice) {
        throw "No installed Windows speech voice matches language '$($payload.language)'."
    }
    $synth.SelectVoice($voice.VoiceInfo.Name)
    $synth.SetOutputToWaveFile([string]$payload.output)
    $synth.Speak([string]$payload.text)
    $synth.Dispose()
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
"""


def _validate_wav(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise AudioGenerationError("The local audio engine did not create a WAV file.")
    try:
        with wave.open(str(path), "rb") as audio:
            if audio.getnframes() <= 0 or audio.getframerate() <= 0:
                raise AudioGenerationError("The local audio engine created an empty WAV file.")
    except (wave.Error, OSError) as exc:
        raise AudioGenerationError("The local audio engine created an unreadable WAV file.") from exc


def synthesize_windows_speech(text: str, language: str, out_path: Path) -> None:
    """Use an already-installed Windows SAPI voice; this never downloads voices."""
    if os.name != "nt":
        raise AudioGenerationError("Local Windows narration is available only on Windows.")
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        raise AudioGenerationError("Windows PowerShell was not found, so local narration is unavailable.")
    if not text.strip():
        raise AudioGenerationError("There is no narration text in this story.")

    payload = json.dumps({"text": text, "language": language, "output": str(out_path.resolve())},
                         ensure_ascii=False)
    encoded_payload = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    encoded_script = base64.b64encode(_SPEECH_SCRIPT.encode("utf-16le")).decode("ascii")
    try:
        result = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_script],
            input=encoded_payload, capture_output=True, text=True, encoding="ascii", errors="replace",
            timeout=600, shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioGenerationError("Local narration did not finish within 10 minutes.") from exc
    except OSError as exc:
        raise AudioGenerationError(f"Could not start Windows local narration: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or "Windows Speech did not provide an error message.").strip()[-500:]
        raise AudioGenerationError(f"Local narration could not be generated: {detail}")
    _validate_wav(out_path)


def generate_music_bed(ffmpeg: str, out_path: Path, duration_seconds: float) -> None:
    """Create a soft, original synthesized chord bed with FFmpeg's local tone source."""
    expression = (
        "0.025*sin(2*PI*261.63*t)+0.020*sin(2*PI*329.63*t)+"
        "0.015*sin(2*PI*392.00*t)+0.010*sin(2*PI*523.25*t)"
    )
    source = f"aevalsrc={expression}:s=44100:d={duration_seconds:.3f}"
    command = [
        ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", source,
        "-af", "afade=t=in:st=0:d=1,afade=t=out:st="
               f"{max(0.0, duration_seconds - 1.0):.3f}:d=1",
        "-ac", "2", "-c:a", "pcm_s16le", str(out_path),
    ]
    _run_audio_command(command, "Could not create the optional local music bed.")
    _validate_wav(out_path)


def mix_audio(ffmpeg: str, speech_path: Path, music_path: Path, out_path: Path,
              duration_seconds: float) -> None:
    command = [
        ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
        "-i", str(speech_path), "-i", str(music_path),
        "-filter_complex",
        "[0:a]volume=1.0[voice];[1:a]volume=0.22[bed];"
        "[voice][bed]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[out]",
        "-map", "[out]", "-t", f"{duration_seconds:.3f}", "-ac", "2", "-c:a", "pcm_s16le",
        str(out_path),
    ]
    _run_audio_command(command, "Could not mix the optional local audio tracks.")
    _validate_wav(out_path)


def _run_audio_command(command: list[str], error_message: str) -> None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=600, shell=False)
    except subprocess.TimeoutExpired as exc:
        raise AudioGenerationError(f"{error_message} FFmpeg exceeded 10 minutes.") from exc
    except OSError as exc:
        raise AudioGenerationError(f"{error_message} {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip()[-500:]
        raise AudioGenerationError(f"{error_message} {detail}".strip())
