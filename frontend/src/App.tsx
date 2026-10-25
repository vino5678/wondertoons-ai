import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { api, ApiError } from "./api/client";
import { Icon, type IconName } from "./components/Icon";
import { ExportPanel } from "./components/ExportPanel";
import { CharacterStudio } from "./components/CharacterStudio";
import type { HealthResponse, Job, Project, StoryPlan, StoryRequest } from "./types/api";

type Page = "dashboard" | "projects" | "characters";

const languageNames: Record<string, string> = {
  en: "English",
  ta: "தமிழ் · Tamil",
};

const languageName = (code: string) => languageNames[code] ?? code.toUpperCase();
const formatDate = (value: string) =>
  new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
const formatDuration = (seconds: number) =>
  seconds >= 60 ? `${Math.floor(seconds / 60)}m ${seconds % 60 ? `${seconds % 60}s` : ""}`.trim() : `${seconds}s`;

function friendlyError(error: unknown): string {
  if (error instanceof ApiError) return error.hint ? `${error.message} ${error.hint}` : error.message;
  return error instanceof Error ? error.message : "Something unexpected happened. Please try again.";
}

function projectTitle(prompt: string): string {
  const firstLine = prompt.trim().split(/\r?\n/)[0].trim();
  return firstLine.length > 58 ? `${firstLine.slice(0, 55).trimEnd()}...` : firstLine;
}

function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [prompt, setPrompt] = useState("");
  const [videoTitle, setVideoTitle] = useState("");
  const [educationalObjective, setEducationalObjective] = useState("");
  const [language, setLanguage] = useState("en");
  const [subtitleLanguage, setSubtitleLanguage] = useState("");
  const [duration, setDuration] = useState("60");
  const [customDuration, setCustomDuration] = useState("");
  const [ageGroup, setAgeGroup] = useState<StoryRequest["age_group"]>("6-8");
  const [animationStyle, setAnimationStyle] = useState("colorful 2D cartoon");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [healthError, setHealthError] = useState("");
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [story, setStory] = useState<StoryPlan | null>(null);
  const [isOpeningProject, setIsOpeningProject] = useState(false);
  const [selectedCharacterIds, setSelectedCharacterIds] = useState<string[]>([]);

  const refreshProjects = useCallback(async () => {
    const result = await api.listProjects();
    setProjects(result);
    return result;
  }, []);

  const refreshHealth = useCallback(async () => {
    try {
      const result = await api.getHealth();
      setHealth(result);
      setHealthError("");
      setLanguage((current) => result.supported_languages.includes(current) ? current :
        (result.supported_languages[0] ?? "en"));
      try {
        await refreshProjects();
        setError((current) => current.startsWith("Could not connect to the backend") ? "" : current);
      } catch (err) {
        setError(friendlyError(err));
      }
    } catch (err) {
      setHealthError(friendlyError(err));
    }
  }, [refreshProjects]);

  useEffect(() => {
    let mounted = true;
    Promise.all([api.getHealth(), api.listProjects()])
      .then(([healthResult, projectResult]) => {
        if (!mounted) return;
        setHealth(healthResult);
        setHealthError("");
        setLanguage((current) => healthResult.supported_languages.includes(current) ? current :
          (healthResult.supported_languages[0] ?? "en"));
        setProjects(projectResult);
      })
      .catch((err: unknown) => {
        if (mounted) {
          setHealthError(friendlyError(err));
          setError(friendlyError(err));
        }
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    if (!activeJob) return;
    let cancelled = false;
    let timer = 0;

    const poll = async () => {
      try {
        const latest = await api.getJob(activeJob.id);
        if (cancelled) return;
        setActiveJob(latest);
        if (latest.status === "completed") {
          const result = await api.getStory(latest.project_id);
          if (cancelled) return;
          setStory(result);
          const refreshed = await refreshProjects();
          setActiveProject(refreshed.find((item) => item.id === latest.project_id) ?? null);
        } else if (latest.status === "failed") {
          setError(latest.error_message || "Story generation failed. Your prompt and project are saved.");
        } else if (latest.status === "cancelled") {
          setError("Story generation was cancelled. Your project and prompt are still saved.");
        } else {
          timer = window.setTimeout(poll, 1400);
        }
      } catch (err) {
        if (cancelled) return;
        setError(`Could not check generation progress: ${friendlyError(err)}`);
        timer = window.setTimeout(poll, 4000);
      }
    };

    timer = window.setTimeout(poll, 1000);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [activeJob?.id, refreshProjects]);

  const supportedLanguages = health?.supported_languages ?? [];
  const readyProjectCount = useMemo(() => projects.filter((project) => project.has_story).length, [projects]);

  async function handleGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const requestedDuration = duration === "custom" ? Number(customDuration) : Number(duration);
    if (prompt.trim().length < 3) {
      setError("Add a story idea with at least 3 characters to get started.");
      return;
    }
    if (!Number.isInteger(requestedDuration) || requestedDuration < 10 || requestedDuration > 3600) {
      setError("Choose a whole-number duration between 10 seconds and 60 minutes.");
      return;
    }
    if (!health || health.status !== "ok") {
      setError("The backend is not ready yet. Check the connection and try again.");
      return;
    }

    setIsSubmitting(true);
    setError("");
    setStory(null);
    setActiveJob(null);
    setActiveProject(null);
    let createdProject: Project | null = null;
    try {
      createdProject = await api.createProject({
        title: videoTitle.trim() || projectTitle(prompt) || "Untitled story",
        prompt: prompt.trim(),
      });
      setActiveProject(createdProject);
      await refreshProjects();
      const request: StoryRequest = {
        prompt: prompt.trim(),
        target_language: language,
        subtitle_languages: subtitleLanguage && subtitleLanguage !== language ? [subtitleLanguage] : [],
        age_group: ageGroup,
        duration_seconds: requestedDuration,
        animation_style: animationStyle,
        educational_objectives: educationalObjective.trim() ? [educationalObjective.trim()] : [],
        character_ids: selectedCharacterIds,
      };
      const job = await api.startStory(createdProject.id, request);
      setActiveJob(job);
    } catch (err) {
      if (createdProject) {
        setActiveProject(createdProject);
        try {
          await refreshProjects();
        } catch (refreshError) {
          setError(`${friendlyError(err)} The project was created, but the project list could not refresh: ${friendlyError(refreshError)}`);
          setIsSubmitting(false);
          return;
        }
        setError(`The project was saved, but story generation could not start: ${friendlyError(err)}`);
      } else {
        setError(friendlyError(err));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function openProject(project: Project) {
    setActiveProject(project);
    setStory(null);
    setActiveJob(null);
    setError("");
    setIsOpeningProject(true);
    try {
      setStory(await api.getStory(project.id));
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError("This project does not have a saved story yet. Start with its prompt in the dashboard.");
      } else {
        setError(friendlyError(err));
      }
    } finally {
      setIsOpeningProject(false);
    }
  }

  const connectionOkay = health?.status === "ok" && health.database === "ok";
  const navItems: { id: Page; label: string; icon: IconName }[] = [
    { id: "dashboard", label: "Dashboard", icon: "home" },
    { id: "projects", label: "My projects", icon: "projects" },
    { id: "characters", label: "Character studio", icon: "characters" },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={(event) => { event.preventDefault(); setPage("dashboard"); }}>
          <span className="brand-mark"><Icon name="spark" /></span>
          <span className="brand-name">wonder<span>toons</span><small>AI STUDIO</small></span>
        </a>
        <div className="workspace-label">WORKSPACE</div>
        <nav aria-label="Main navigation" className="main-nav">
          {navItems.map((item) => (
            <button key={item.id} className={`nav-link ${page === item.id ? "active" : ""}`}
              onClick={() => setPage(item.id)} aria-current={page === item.id ? "page" : undefined}>
              <Icon name={item.icon} /><span>{item.label}</span>
              {item.id === "projects" && <span className="nav-count">{projects.length}</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className={`connection-card ${connectionOkay ? "is-connected" : "is-offline"}`}>
          <span className="connection-indicator" />
          <div><strong>{connectionOkay ? "Studio connected" : "Connecting to studio"}</strong>
            <small>{connectionOkay ? `API v${health.version}` : "Waiting for backend"}</small></div>
          <button className="icon-button" aria-label="Retry backend connection" onClick={refreshHealth}><Icon name="refresh" /></button>
        </div>
        <div className="sidebar-footer">Made for little big imaginations <span>✦</span></div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb"><span>Studio</span><span className="breadcrumb-divider">/</span>
            <strong>{page === "dashboard" ? "Dashboard" : page === "projects" ? "My projects" : "Character studio"}</strong></div>
          <div className="topbar-right">
            <span className={`status-pill ${connectionOkay ? "connected" : "offline"}`}><span />{connectionOkay ? "All systems ready" : "Backend offline"}</span>
            <div className="avatar" aria-label="WonderToons workspace">W</div>
          </div>
        </header>

        <div className="page-wrap">
          {page === "dashboard" ? (
            <DashboardPage
              error={error}
              healthError={healthError}
              isLoading={isLoading}
              isSubmitting={isSubmitting}
              activeJob={activeJob}
              activeProject={activeProject}
              story={story}
              selectedCharacterCount={selectedCharacterIds.length}
              projects={projects}
              readyProjectCount={readyProjectCount}
              prompt={prompt}
              videoTitle={videoTitle}
              educationalObjective={educationalObjective}
              language={language}
              subtitleLanguage={subtitleLanguage}
              supportedLanguages={supportedLanguages}
              duration={duration}
              customDuration={customDuration}
              ageGroup={ageGroup}
              animationStyle={animationStyle}
              onPromptChange={setPrompt}
              onVideoTitleChange={setVideoTitle}
              onEducationalObjectiveChange={setEducationalObjective}
              onLanguageChange={(value) => { setLanguage(value); if (subtitleLanguage === value) setSubtitleLanguage(""); }}
              onSubtitleLanguageChange={setSubtitleLanguage}
              onDurationChange={setDuration}
              onCustomDurationChange={setCustomDuration}
              onAgeGroupChange={setAgeGroup}
              onAnimationStyleChange={setAnimationStyle}
              onGenerate={handleGenerate}
              onOpenProject={openProject}
              onProjectsClick={() => setPage("projects")}
              onCharactersClick={() => setPage("characters")}
            />
          ) : page === "projects" ? (
            <ProjectsPage projects={projects} isLoading={isLoading} isOpeningProject={isOpeningProject}
              activeProject={activeProject} story={story} error={error} onOpenProject={openProject}
              onCreateClick={() => setPage("dashboard")} />
          ) : (
            <CharacterStudio selectedIds={selectedCharacterIds} onSelectionChange={setSelectedCharacterIds}
              onCreateStory={() => setPage("dashboard")} />
          )}
        </div>
      </main>
    </div>
  );
}

interface DashboardPageProps {
  error: string;
  healthError: string;
  isLoading: boolean;
  isSubmitting: boolean;
  activeJob: Job | null;
  activeProject: Project | null;
  story: StoryPlan | null;
  selectedCharacterCount: number;
  projects: Project[];
  readyProjectCount: number;
  prompt: string;
  videoTitle: string;
  educationalObjective: string;
  language: string;
  subtitleLanguage: string;
  supportedLanguages: string[];
  duration: string;
  customDuration: string;
  ageGroup: StoryRequest["age_group"];
  animationStyle: string;
  onPromptChange: (value: string) => void;
  onVideoTitleChange: (value: string) => void;
  onEducationalObjectiveChange: (value: string) => void;
  onLanguageChange: (value: string) => void;
  onSubtitleLanguageChange: (value: string) => void;
  onDurationChange: (value: string) => void;
  onCustomDurationChange: (value: string) => void;
  onAgeGroupChange: (value: StoryRequest["age_group"]) => void;
  onAnimationStyleChange: (value: string) => void;
  onGenerate: (event: FormEvent<HTMLFormElement>) => void;
  onOpenProject: (project: Project) => void;
  onProjectsClick: () => void;
  onCharactersClick: () => void;
}

function DashboardPage(props: DashboardPageProps) {
  const running = props.activeJob && ["queued", "running"].includes(props.activeJob.status);
  return (
    <>
      <section className="welcome-row">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" /> YOUR CREATIVE WORKSPACE</div>
          <h1>Let’s make something <span>wonderful.</span></h1>
          <p>Turn a little idea into a big story for curious minds.</p>
        </div>
        <div className="welcome-art" aria-hidden="true">
          <div className="art-sun" /><div className="art-hill art-hill-back" /><div className="art-hill art-hill-front" />
          <div className="art-star">✦</div><div className="art-cloud">☁</div>
          <div className="art-caption">IDEAS<br />TAKE FLIGHT</div>
        </div>
      </section>

      {props.healthError && <div className="alert-banner" role="alert"><Icon name="alert" /><span>{props.healthError}</span></div>}

      <section className="composer-card">
        <div className="section-heading composer-heading">
          <div className="heading-icon purple"><Icon name="wand" /></div>
          <div><h2>Start with a story idea</h2><p>Your next classroom favourite begins right here.</p></div>
          <span className="step-tag">01 <span>·</span> YOUR IDEA</span>
        </div>
        <form onSubmit={props.onGenerate}>
          <label className="sr-only" htmlFor="story-prompt">Describe the story you want to create</label>
          <textarea id="story-prompt" className="prompt-input" value={props.prompt} maxLength={2000}
            onChange={(event) => props.onPromptChange(event.target.value)}
            placeholder="A curious little cloud learns why the rain helps flowers grow..." />
          <div className="prompt-foot"><span>Be as imaginative as you like — one sentence is plenty.</span>
            <span>{props.prompt.length} / 2000</span></div>
          <div className="form-divider" />
          <div className="composer-options">
            <label className="field">
              <span>Video title <small>optional</small></span>
              <input value={props.videoTitle} maxLength={120}
                onChange={(event) => props.onVideoTitleChange(event.target.value)}
                placeholder="A title for your video" />
            </label>
            <label className="field">
              <span>Learning goal <small>optional</small></span>
              <input value={props.educationalObjective} maxLength={200}
                onChange={(event) => props.onEducationalObjectiveChange(event.target.value)}
                placeholder="What should children learn?" />
            </label>
            <label className="field">
              <span>Story language</span>
              <select value={props.language} onChange={(event) => props.onLanguageChange(event.target.value)}
                disabled={!props.supportedLanguages.length} required>
                {props.supportedLanguages.map((code) => <option key={code} value={code}>{languageName(code)}</option>)}
              </select>
            </label>
            <label className="field">
              <span>Captions <small>optional</small></span>
              <select value={props.subtitleLanguage} onChange={(event) => props.onSubtitleLanguageChange(event.target.value)}>
                <option value="">No extra captions</option>
                {props.supportedLanguages.filter((code) => code !== props.language).map((code) =>
                  <option key={code} value={code}>{languageName(code)}</option>)}
              </select>
            </label>
            <label className="field">
              <span>Story length</span>
              <select value={props.duration} onChange={(event) => props.onDurationChange(event.target.value)}>
                <option value="30">Quick · 30 sec</option><option value="60">Short · 1 min</option>
                <option value="120">Medium · 2 min</option><option value="300">Long · 5 min</option>
                <option value="custom">Custom length</option>
              </select>
            </label>
            {props.duration === "custom" && <label className="field custom-duration">
              <span>Seconds <small>10–3600</small></span>
              <input type="number" min="10" max="3600" step="1" value={props.customDuration}
                onChange={(event) => props.onCustomDurationChange(event.target.value)} placeholder="e.g. 180" required />
            </label>}
            <label className="field">
              <span>For ages</span>
              <select value={props.ageGroup} onChange={(event) => props.onAgeGroupChange(event.target.value as StoryRequest["age_group"])}>
                <option value="3-5">3–5 years</option><option value="6-8">6–8 years</option><option value="9-12">9–12 years</option>
              </select>
            </label>
            <label className="field">
              <span>Animation style</span>
              <select value={props.animationStyle} onChange={(event) => props.onAnimationStyleChange(event.target.value)}>
                <option value="colorful 2D cartoon">Colourful 2D cartoon</option>
                <option value="storybook illustration">Storybook illustration</option>
                <option value="paper cutout">Paper cutout</option>
                <option value="soft 3D cartoon">Soft 3D cartoon</option>
              </select>
            </label>
          </div>
          <div className="composer-actions">
            <span className="privacy-note"><Icon name="leaf" /> Your stories are saved to this studio.</span>
            <button type="button" className="text-button selected-cast-link" onClick={props.onCharactersClick}>
              <Icon name="characters" /> {props.selectedCharacterCount
                ? `${props.selectedCharacterCount} character${props.selectedCharacterCount === 1 ? "" : "s"} selected`
                : "Choose characters"}
            </button>
            <button className="primary-button" type="submit" disabled={props.isSubmitting || Boolean(running) || !props.supportedLanguages.length}>
              {props.isSubmitting ? <><span className="button-spinner" /> Saving idea...</> :
                running ? <><span className="button-spinner" /> Story in progress...</> :
                  <>Create story script <Icon name="arrow" /></>}
            </button>
          </div>
        </form>
      </section>

      {props.error && <div className="alert-banner error-banner" role="alert"><Icon name="alert" />
        <span>{props.error}</span></div>}

      {(props.activeJob || props.story) && (
        <StoryResult job={props.activeJob} story={props.story} projectId={props.activeProject?.id}
          videoTitle={props.activeProject?.title} />
      )}

      <section className="stats-grid" aria-label="Project overview">
        <StatCard label="Your projects" value={String(props.projects.length)} detail="Ideas in your studio" icon="projects" tone="lavender" />
        <StatCard label="Stories created" value={String(props.readyProjectCount)} detail="Saved story plans" icon="spark" tone="mint" />
        <StatCard label="Languages ready" value={String(props.supportedLanguages.length)} detail={props.supportedLanguages.map(languageName).join(" · ") || "Connect backend"} icon="leaf" tone="peach" />
      </section>

      <section className="recent-section">
        <div className="section-heading recent-heading"><div><h2>Your recent projects</h2>
          <p>Pick up where your imagination left off.</p></div>
          <button className="text-button" onClick={props.onProjectsClick}>See all projects <Icon name="arrow" /></button>
        </div>
        {props.isLoading ? <div className="empty-card"><span className="loading-dot" /> Loading your studio...</div> :
          props.projects.length ? <div className="project-grid">
            {props.projects.slice(0, 3).map((project, index) => <ProjectCard key={project.id} project={project} index={index}
              onOpen={() => props.onOpenProject(project)} />)}
          </div> : <EmptyProjects />}
      </section>
    </>
  );
}

function StoryResult({ job, story, projectId, videoTitle }: {
  job: Job | null;
  story: StoryPlan | null;
  projectId?: string;
  videoTitle?: string;
}) {
  const running = job && ["queued", "running"].includes(job.status);
  return (
    <section className="story-result" aria-live="polite">
      {running && <div className="progress-card">
        <span className="progress-orbit"><Icon name="spark" /></span>
        <div className="progress-copy"><strong>{job.status === "queued" ? "Your idea is in the queue" : "Your story is taking shape"}</strong>
          <span>{job.stage.replace(/_/g, " ")} · stage-based progress, not measured work</span></div>
        <div className="progress-meter"><span style={{ width: `${job.progress}%` }} /></div>
        <strong className="progress-number">{job.progress}%</strong>
      </div>}
      {story && <div className="story-card">
        <div className="story-topline"><div><span className="eyebrow"><span className="eyebrow-line" /> YOUR STORY PLAN</span>
          <h2>{story.title}</h2></div>
          <div className={`output-tag ${story.output_status}`}>{story.output_status === "mock" ? "Preview · mock story" : story.output_status}</div>
        </div>
        <p className="story-synopsis">{story.synopsis}</p>
        {story.warnings.length > 0 && <div className="story-warning"><Icon name="alert" />{story.warnings.join(" ")}</div>}
        <div className="story-meta">{formatDuration(story.total_duration_seconds)} <span>·</span> {languageName(story.target_language)}
          <span>·</span> {story.scenes.length} scenes <span>·</span> Provider: {story.provider}</div>
        <div className="scene-list">
          {story.scenes.map((scene) => <article className="scene-row" key={scene.scene_id}>
            <span className="scene-number">{String(scene.order).padStart(2, "0")}</span>
            <div className="scene-info"><strong>{scene.title}</strong><p>{scene.description || scene.narration || scene.visual_prompt}</p>
              {scene.narration && <span className="scene-narration">“{scene.narration}”</span>}</div>
            <span className="scene-duration">{scene.estimated_duration_seconds}s</span>
          </article>)}
        </div>
        <p className="mock-note"><Icon name="spark" /> This is a mock text story plan from the configured provider—not a rendered animation.</p>
      </div>}
      {story && projectId && <ExportPanel key={projectId} projectId={projectId} story={story} initialTitle={videoTitle} />}
    </section>
  );
}

function StatCard({ label, value, detail, icon, tone }: { label: string; value: string; detail: string; icon: IconName; tone: string }) {
  return <article className="stat-card"><div className={`stat-icon ${tone}`}><Icon name={icon} /></div>
    <div><span className="stat-label">{label}</span><strong>{value}</strong><small>{detail}</small></div></article>;
}

function ProjectCard({ project, index, onOpen }: { project: Project; index: number; onOpen: () => void }) {
  return <article className={`project-card project-card-${index % 3}`}>
    <div className="project-thumb" aria-hidden="true"><div className="thumb-sun" /><div className="thumb-shape shape-one" />
      <div className="thumb-shape shape-two" /><span className="thumb-spark">✦</span>
      <span className={`project-state ${project.has_story ? "ready" : "draft"}`}>{project.has_story ? "STORY READY" : "IDEA SAVED"}</span></div>
    <div className="project-card-body"><h3>{project.title}</h3><p>{project.prompt || "No prompt added yet."}</p>
      <div className="project-card-meta"><span><Icon name="clock" />{formatDate(project.updated_at)}</span>
        <span>{project.scene_count ? `${project.scene_count} scenes` : "No scenes yet"}</span></div>
      <button className="project-open" onClick={onOpen}>{project.has_story ? "Open story" : "View project"} <Icon name="arrow" /></button>
    </div>
  </article>;
}

function EmptyProjects() {
  return <div className="empty-card empty-projects"><div className="empty-illustration"><Icon name="spark" /></div>
    <strong>Your next favourite story starts with an idea.</strong>
    <span>Write a prompt above and your saved projects will show up here.</span></div>;
}

function ProjectsPage({ projects, isLoading, isOpeningProject, activeProject, story, error, onOpenProject, onCreateClick }: {
  projects: Project[];
  isLoading: boolean;
  isOpeningProject: boolean;
  activeProject: Project | null;
  story: StoryPlan | null;
  error: string;
  onOpenProject: (project: Project) => void;
  onCreateClick: () => void;
}) {
  return <section className="projects-page">
    <div className="page-title-row"><div><div className="eyebrow"><span className="eyebrow-line" /> YOUR LIBRARY</div>
      <h1>My projects</h1><p>Every story idea, together in one happy place.</p></div>
      <button className="primary-button" onClick={onCreateClick}><Icon name="plus" /> New story</button></div>
    {error && <div className="alert-banner error-banner" role="alert"><Icon name="alert" /><span>{error}</span></div>}
    {activeProject && (isOpeningProject || story) && <div className="project-story-panel">
      {isOpeningProject ? <div className="empty-card"><span className="loading-dot" /> Opening saved story...</div> :
        <StoryResult job={null} story={story} projectId={activeProject.id} videoTitle={activeProject.title} />}
    </div>}
    {isLoading ? <div className="empty-card"><span className="loading-dot" /> Loading your studio...</div> :
      projects.length ? <div className="project-grid full-project-grid">
        {projects.map((project, index) => <ProjectCard key={project.id} project={project} index={index}
          onOpen={() => onOpenProject(project)} />)}
      </div> : <EmptyProjects />}
  </section>;
}

export default App;
