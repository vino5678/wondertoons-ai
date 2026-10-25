export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  database: "ok" | "error";
  ffmpeg_available: boolean;
  ffprobe_available: boolean;
  default_story_provider: string;
  available_story_providers: string[];
  supported_languages: string[];
  external_llm_configured: boolean;
  network_features_enabled: boolean;
}

export interface Project {
  id: string;
  title: string;
  prompt: string;
  provider_settings: Record<string, unknown>;
  has_story: boolean;
  scene_count: number;
  selected_character_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface CreateProjectRequest {
  title: string;
  prompt: string;
  provider_settings?: Record<string, unknown>;
}

export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface Job {
  id: string;
  project_id: string;
  kind: string;
  status: JobStatus;
  stage: string;
  progress: number;
  progress_kind: string;
  error_message: string | null;
  output_files: string[];
  created_at: string;
  updated_at: string;
}

export interface StoryRequest {
  prompt: string;
  target_language: string;
  subtitle_languages: string[];
  age_group: "3-5" | "6-8" | "9-12";
  duration_seconds: number;
  animation_style: string;
  educational_objectives?: string[];
  character_ids?: string[];
}

export interface Character {
  id: string;
  name: string;
  description: string;
  appearance: string;
  personality: string;
  voice_preferences: { language?: string | null; style?: string | null; pitch?: string | null; provider_voice_id?: string | null };
  reference_image_paths: string[];
  created_at: string;
  updated_at: string;
}

export interface CharacterCreateRequest {
  name: string;
  description: string;
  appearance: string;
  personality: string;
}

export interface DialogueLine {
  character_id: string;
  text: string;
  language: string;
}

export interface Scene {
  scene_id: string;
  order: number;
  title: string;
  description: string;
  character_ids: string[];
  dialogue: DialogueLine[];
  narration: string;
  audio_cues: string[];
  visual_prompt: string;
  estimated_duration_seconds: number;
  caption_text: Record<string, string>;
  previous_scene_id: string | null;
  next_scene_id: string | null;
}

export interface StoryPlan {
  title: string;
  synopsis: string;
  target_language: string;
  subtitle_languages: string[];
  age_group: "3-5" | "6-8" | "9-12";
  total_duration_seconds: number;
  duration_tolerance_seconds: number;
  provider: string;
  output_status: "mock" | "generated" | "pending" | "failed";
  characters_used: { id: string; name: string }[];
  warnings: string[];
  scenes: Scene[];
}

export type AspectRatio = "16:9" | "9:16" | "1:1";
export type Resolution = "480p" | "720p" | "1080p";
export type VideoRenderer = "procedural_2d" | "storyboard_preview";

export interface ExportRequest {
  title?: string;
  renderer: VideoRenderer;
  aspect_ratio: AspectRatio;
  resolution: Resolution;
  caption_languages: string[];
  burn_captions: boolean;
  narration: boolean;
  background_music: boolean;
  include_silent_audio: boolean;
}

export interface ExportFile {
  name: string;
  kind: "video" | "subtitles_srt" | "subtitles_vtt" | "manifest" | string;
  size_bytes: number;
  url: string;
}

export interface ExportManifest {
  kind: string;
  is_ai_generated_video: boolean;
  renderer: string;
  visual_generation: string;
  video_title: string;
  width: number;
  height: number;
  aspect_ratio: AspectRatio;
  resolution: Resolution;
  measured_duration_seconds: number;
  audio: string;
  warnings: string[];
}

export interface ExportItem {
  job_id: string;
  status: JobStatus;
  created_at: string;
  kind: string;
  files: ExportFile[];
  manifest: ExportManifest | null;
}

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    hint?: string | null;
  };
  detail?: unknown;
}
