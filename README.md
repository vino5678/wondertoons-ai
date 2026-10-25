# WonderToons AI Studio

WonderToons turns a prompt into a reviewable story/scene plan and can render that plan to a local,
browser-playable MP4. It does not call a paid service or download an AI model.

## What the video renderer actually creates

The default `procedural_2d` renderer produces simple illustrated scenes locally:

- Python reads each scene's prompt text and selects from procedural settings (including forest,
  beach, underwater, space, city, farm, classroom, desert, mountains, and castle), props, and
  character drawings. Each scene gets its own character image; common action words select walking,
  flying, swimming, dancing, jumping, or resting movement.
- The mock story provider still creates templated narration, but now carries the complete prompt
  into scene planning and splits timestamped scripts into separate scene beats. The procedural
  renderer recognizes common prompt characters such as watermelon, banana, and orange, and includes
  named prompt characters in scene drawings when they are supported.
- FFmpeg animates the scene character, adds titles/captions and transitions, encodes H.264 video and
  AAC audio, and writes an MP4.
- `ffprobe` checks that the file exists, is readable, has the requested frame size/codecs, and has
  approximately the requested duration before it is made available to preview/download.
- The old `storyboard_preview` title-card renderer remains available as an explicit option.

This is **procedural 2D animation**, not full AI-generated video and not AI-generated imagery.
Drawings are built from a finite set of geometric scenes and recognizable shapes. Keyword matching
cannot understand every subject or action; unsupported details may be represented only by the
closest available setting/prop or a generic character. It does not make photorealistic imagery,
lip-sync, or detailed character acting. The existing `mock` story provider still creates templated
text, not AI-written stories. The story plan is shown for adult review before rendering.

The optional music bed is synthesized from quiet tones by FFmpeg; it is not a licensed music
recording or a sound-effect library. Optional narration uses an already-installed Windows
`System.Speech` voice, entirely on the computer. Voice availability depends on the language voices
installed in Windows. On the inspected laptop, English voices were present and Tamil voices were
not; requesting narration for an unsupported installed language produces a warning and the video
continues without speech.

## Character Studio

The Character Studio is local and uses the existing character database. Save a starter character or
create a profile with an appearance and personality, select up to ten characters, then choose
**Create a story**. The selected character IDs and descriptions are included in the story plan and
procedural scene artwork. The drawings use locally generated shapes, shading, and facial details;
they are stylized illustrations, not photorealistic or AI-generated character images. Unsupported
species and fine appearance details may not be depicted exactly.

## Local cost, privacy, licenses, and model decision

- No paid APIs, credits, cloud GPU, subscription, billing, video model, image model, or model
  download is used by this renderer. Prompts and scripts are passed only to local app processes.
- The existing DM Sans and Manrope typography is bundled locally from Fontsource packages under
  SIL Open Font License 1.1, so the frontend makes no Google Fonts request at runtime.
- Story/video rendering is local; FFmpeg and Windows speech execute as local programs. The backend
  network-provider switch defaults to `false`. The `external_llm` provider is still a stub and
  remains unavailable unless an adult deliberately enables the switch; enabling it does not make
  that provider implemented.
- Python application code uses the Python standard library for the procedural drawings. The
  WinGet Gyan FFmpeg Shared build is explicitly listed as GPL-3.0 by WinGet and Gyan describes its
  Windows builds as GPLv3. Review that license before redistributing the binary or a combined
  application. This package is free to install; it does not enable cloud inference or billing.
- Windows `System.Speech` and the individual installed voice terms are governed by the Windows
  installation/license; this app does not download, redistribute, or bundle a voice.

### Why this does not use a text-to-video model

The inspected computer is an ASUS Vivobook with an Intel i5-13420H, 15.7 GB RAM, Intel UHD graphics,
and an NVIDIA RTX 3050 Laptop GPU reporting 4 GB VRAM. CogVideoX-2B is a genuine text-to-video
candidate whose upstream repository describes an Apache-2.0 model license, but its upstream README
references a GTX 1080 Ti for the 2B model and its low-memory table is based on optimized runs tested
on A100/H100-class GPUs. A 4 GB laptop GPU is not a verified or reliable target for that workload;
model weights are multi-gigabyte, inference is likely to be very slow or fail under Windows GPU
memory pressure. We therefore do not integrate or download it.

Piper is a local open-source TTS candidate (`piper-tts`, GPL-3.0 project code). Its official docs
say it is intended for personal use and TTS research, and each voice has a separate model card/license;
every voice also needs an ONNX model plus config download. The listed English Lessac medium ONNX
file is about 63 MB, before its config; exact sizes depend on voice. The current official voice list
does not include Tamil. Piper is not installed or required here. No Piper voice model is bundled or
downloaded.

References: [CogVideoX-2B model card](https://huggingface.co/THUDM/CogVideoX-2b),
[Piper project](https://github.com/OHF-Voice/piper1-gpl),
[Piper voice licensing guidance](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md),
[Microsoft SpeechSynthesizer API](https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.speechsynthesizer),
[Gyan FFmpeg build/licensing notes](https://www.gyan.dev/ffmpeg/builds/), and
[Fontsource DM Sans](https://fontsource.org/fonts/dm-sans) / [Manrope](https://fontsource.org/fonts/manrope),
[FFmpeg legal information](https://ffmpeg.org/legal.html).

## Requirements

- Windows 10/11, Python 3.10+ (Python 3.12 recommended), Node.js 18+ and npm.
- FFmpeg and FFprobe on `PATH` for rendering. The inspected laptop initially lacked FFmpeg; the
  free Gyan 9.0.2 GPL-3.0 shared build has since been installed for validation.
- No NVIDIA GPU or neural model is required for procedural rendering.
- A 16 GB RAM machine is sufficient for this light renderer. CPU time grows with video duration,
  resolution, and scene count. Start at 480p. 720p/1080p are available but take longer.
- Work files are temporary and cleaned after a job; final MP4/subtitle/manifest files are kept in
  `data/projects/<project-id>/exports/`.

## Windows installation

From the project root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Install the free FFmpeg/FFprobe package with WinGet (package ID verified against the WinGet source):

```powershell
winget install --id Gyan.FFmpeg.Shared --exact --source winget
```

Close and reopen PowerShell after installation (fully restart VS Code if using its integrated
terminal so it inherits the refreshed PATH), then verify both tools:

```powershell
ffmpeg -version
ffprobe -version
```

If they are not on `PATH`, set `WONDERTOONS_FFMPEG_PATH` and
`WONDERTOONS_FFPROBE_PATH` in `.env` to their absolute executable paths, then restart the backend.
No AI model weights need to be downloaded. FFmpeg installation and optional software downloads
consume internet data and disk space even though they do not incur API charges.

Install the frontend dependencies in a second PowerShell:

```powershell
cd frontend
npm install
```

## Start the app

PowerShell window 1, from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload --port 8001
```

PowerShell window 2:

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5174`. The frontend proxy targets this workspace's backend on port 8001;
the separate ports avoid collisions with other WonderToons copies. The backend API docs are at
`http://127.0.0.1:8001/docs`.

## Create a test video

1. In the dashboard, enter a story prompt, optional title and learning goal, language, age group,
   duration, and visual style. Choose **Create story script**.
2. Review the generated text and scene plan. Remember the current story provider is templated mock
   text.
3. In **Create Kids Video**, select **Procedural 2D animation**, aspect ratio, output quality, and
   optional narration/music; then click **Create animated video**.
4. Wait for the measured scene-rendering progress. Preview or download the verified MP4 beneath
   the progress display. The manifest reports the measured output duration and any optional audio
   components that could not be generated.

Choose **Storyboard title cards** only when you explicitly want the simpler legacy preview.

## API

- `POST /projects/{project_id}/story`: create a reviewable story plan.
- `POST /projects/{project_id}/exports`: queue a local video export; `renderer` defaults to
  `procedural_2d` and may be `storyboard_preview`.
- `GET /jobs/{job_id}`: poll measured scene progress.
- `GET /projects/{project_id}/exports`: list completed exports.
- `GET /projects/{project_id}/exports/{job_id}/files/{filename}`: stream a preview or download with
  `?download=1`.

The export request supports title, renderer, `16:9`/`9:16`/`1:1`, `480p`/`720p`/`1080p`, caption
languages, captions on/off, local narration on/off, and synthesized music on/off.

## Tests and limitations

Run backend tests from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
python -m pytest -v
```

FFmpeg integration tests skip when FFmpeg/FFprobe are missing; pure validation, procedural asset,
API, and local narration tests do not require AI models or paid services. No test here can establish
full AI video generation because that capability is intentionally not implemented.

Limitations:

- The story generator remains deterministic template text, not a local LLM.
- The renderer uses finite geometric art and prompt keyword rules. It does not understand arbitrary
  prompts like a language model, generate original AI imagery, create photorealistic video, lip-sync,
  or provide detailed multi-character acting. Review scenes before rendering; unusual or unsupported
  subjects may not appear faithfully.
- Windows narration depends on an installed matching voice and its terms; current inspected
  hardware has English voices only. Tamil narration is therefore not available by default.
- Captions follow estimated scene timing, not word-level speech alignment. Narration runs over the
  video from its beginning and may have silence after it; video duration remains the measured target.
- The generated music is a quiet tone bed, not a full soundtrack. No third-party SFX/music is
  bundled.
- Resolution and long durations can make CPU encoding slow. No rendering-speed promise is made;
  the actual measured duration is shown in the export manifest and UI.
