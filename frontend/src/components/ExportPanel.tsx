import { useCallback, useEffect, useState } from "react";
import { api, ApiError, mediaUrl } from "../api/client";
import { Icon } from "./Icon";
import type { AspectRatio, ExportItem, Job, Resolution, StoryPlan, VideoRenderer } from "../types/api";

const languageLabel = (code: string) => (code === "ta" ? "தமிழ் · Tamil" : code === "en" ? "English" : code.toUpperCase());
const formatSize = (bytes: number) =>
  bytes >= 1_048_576 ? `${(bytes / 1_048_576).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
const describe = (error: unknown) =>
  error instanceof ApiError ? (error.hint ? `${error.message} ${error.hint}` : error.message)
    : error instanceof Error ? error.message : "Something unexpected happened. Please try again.";

export function ExportPanel({ projectId, story, initialTitle }: {
  projectId: string;
  story: StoryPlan;
  initialTitle?: string;
}) {
  const storyLanguages = Array.from(new Set([story.target_language, ...story.subtitle_languages]));
  const [title, setTitle] = useState(initialTitle || story.title);
  const [renderer, setRenderer] = useState<VideoRenderer>("procedural_2d");
  const [aspect, setAspect] = useState<AspectRatio>("16:9");
  const [resolution, setResolution] = useState<Resolution>("480p");
  const [burnCaptions, setBurnCaptions] = useState(true);
  const [narration, setNarration] = useState(false);
  const [backgroundMusic, setBackgroundMusic] = useState(false);
  const [languages, setLanguages] = useState<string[]>(storyLanguages);
  const [exports, setExports] = useState<ExportItem[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);
  const [tick, setTick] = useState(0);

  const loadExports = useCallback(async () => {
    try {
      setExports(await api.listExports(projectId));
    } catch (err) {
      setError(describe(err));
    }
  }, [projectId]);

  useEffect(() => { void loadExports(); }, [loadExports]);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const latest = await api.getJob(job.id);
        if (cancelled) return;
        setJob(latest);
        if (latest.status === "completed") await loadExports();
        else if (latest.status === "failed") setError(latest.error_message || "The video export failed.");
      } catch (err) {
        if (cancelled) return;
        setError(`Could not check export progress: ${describe(err)}`);
        setTick((n) => n + 1); // try again
      }
    }, 1200);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [job, tick, loadExports]);

  const running = Boolean(job && ["queued", "running"].includes(job.status));

  async function startExport() {
    if (starting || running) return;
    setError("");
    setStarting(true);
    try {
      setJob(await api.startExport(projectId, {
        title: title.trim() || story.title,
        renderer,
        aspect_ratio: aspect,
        resolution,
        caption_languages: languages,
        burn_captions: burnCaptions,
        narration,
        background_music: backgroundMusic,
        include_silent_audio: true,
      }));
    } catch (err) {
      setError(describe(err));
    } finally {
      setStarting(false);
    }
  }

  function toggleLanguage(code: string) {
    setLanguages((current) => (current.includes(code) ? current.filter((c) => c !== code) : [...current, code]));
  }

  const latest = exports[0];
  const video = latest?.files.find((f) => f.kind === "video");
  const manifest = latest?.manifest;

  return (
    <div className="export-panel">
      <div className="export-heading">
        <div><strong>Create Kids Video</strong>
          <p>Render the reviewed scene plan to a local MP4. No video API or model download is used.</p></div>
        <span className="output-tag">Local rendering</span>
      </div>
      <div className="export-controls">
        <label>Video title
          <input value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} disabled={running} />
        </label>
        <label>Visual method
          <select value={renderer} onChange={(e) => setRenderer(e.target.value as VideoRenderer)} disabled={running}>
            <option value="procedural_2d">Procedural 2D animation</option>
            <option value="storyboard_preview">Storyboard title cards</option>
          </select>
        </label>
        <label>Shape
          <select value={aspect} onChange={(e) => setAspect(e.target.value as AspectRatio)} disabled={running}>
            <option value="16:9">Widescreen 16:9</option>
            <option value="9:16">Vertical 9:16</option>
            <option value="1:1">Square 1:1</option>
          </select></label>
        <label>Quality
          <select value={resolution} onChange={(e) => setResolution(e.target.value as Resolution)} disabled={running}>
            <option value="480p">480p (fastest)</option>
            <option value="720p">720p</option>
            <option value="1080p">1080p</option>
          </select></label>
        <label className="export-check"><input type="checkbox" checked={burnCaptions} disabled={running}
          onChange={(e) => setBurnCaptions(e.target.checked)} /> Show captions in video</label>
        <label className="export-check"><input type="checkbox" checked={narration} disabled={running}
          onChange={(e) => setNarration(e.target.checked)} /> Local Windows narration (if a matching voice is installed)</label>
        <label className="export-check"><input type="checkbox" checked={backgroundMusic} disabled={running}
          onChange={(e) => setBackgroundMusic(e.target.checked)} /> Original synthesized music bed</label>
        {storyLanguages.length > 1 && storyLanguages.map((code) => (
          <label className="export-check" key={code}><input type="checkbox" checked={languages.includes(code)}
            disabled={running} onChange={() => toggleLanguage(code)} /> {languageLabel(code)}</label>))}
        <button className="primary-button" onClick={startExport}
          disabled={starting || running || languages.length === 0 || !title.trim()}>
          {starting || running ? <><span className="button-spinner" /> Rendering video...</> : <>Create animated video <Icon name="film" /></>}
        </button>
      </div>
      <p className="mock-note"><Icon name="alert" />
        Procedural animation uses prompt-selected settings, props, characters and movement from a finite set of
        geometric illustrations; unusual details may not be depicted accurately. It is not full AI-generated video.
        The story text remains the configured story provider's output. English narration uses installed Windows voices;
        unavailable requested audio is reported and video rendering continues without it.</p>

      {running && job && <div className="progress-card">
        <span className="progress-orbit"><Icon name="film" /></span>
        <div className="progress-copy"><strong>{job.stage.replace(/_/g, " ")}</strong>
          <span>{job.progress_kind === "scene_count" ? "measured by scenes rendered" : "stage-based, not measured work"}</span></div>
        <div className="progress-meter"><span style={{ width: `${job.progress}%` }} /></div>
        <strong className="progress-number">{job.progress}%</strong>
      </div>}
      {error && <div className="alert-banner error-banner" role="alert"><Icon name="alert" /><span>{error}</span></div>}

      {latest && video && <div className="export-result">
        <video key={latest.job_id} className="export-video" controls preload="metadata" src={mediaUrl(video.url)} />
        <div className="export-links">
          <a className="text-button" href={mediaUrl(`${video.url}?download=1`)}>Download MP4 · {formatSize(video.size_bytes)}</a>
          {latest.files.filter((f) => f.kind === "subtitles_srt").map((f) => (
            <a className="text-button" key={f.name} href={mediaUrl(`${f.url}?download=1`)}>{f.name}</a>))}
        </div>
        {manifest && <div className="export-manifest">
          <p className="mock-note">{manifest.width}×{manifest.height} · {manifest.measured_duration_seconds.toFixed(1)}s actual ·
            {manifest.audio.replace(/_/g, " ")} · {manifest.renderer}</p>
          {manifest.warnings.map((warning) => <p className="story-warning" key={warning}><Icon name="alert" />{warning}</p>)}
        </div>}
        {exports.length > 1 && <p className="mock-note">{exports.length - 1} older export(s) are saved in this project.</p>}
      </div>}
      {!latest && !running && <p className="mock-note">No video has been rendered for this project yet.</p>}
    </div>
  );
}
