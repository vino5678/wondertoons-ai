import { useEffect, useId, useState } from "react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { Icon } from "./Icon";
import type { Character, CharacterCreateRequest } from "../types/api";

const presets: (CharacterCreateRequest & { kind: string; color: string; accent: string })[] = [
  { name: "Milo the Fox", kind: "fox", color: "#e88343", accent: "#ffd69b",
    description: "A thoughtful young fox who looks out for his friends.",
    appearance: "A small orange fox with a cream muzzle, bright amber eyes, soft pointed ears, a fluffy cream-tipped tail, and a teal explorer scarf.",
    personality: "Curious, loyal, and gentle." },
  { name: "Luna the Rabbit", kind: "rabbit", color: "#d9c8ef", accent: "#ffe9ee",
    description: "A gentle rabbit who loves discovering new things.",
    appearance: "A soft light-gray rabbit with long pink-lined ears, warm brown eyes, a tiny pink nose, white paws, and a lavender vest.",
    personality: "Kind, patient, and imaginative." },
  { name: "Nia the Gardener", kind: "human", color: "#ae6e51", accent: "#ffd49b",
    description: "A cheerful child who helps her friends care for the garden.",
    appearance: "A young girl with warm brown skin, dark curly hair in two puffs, expressive brown eyes, a sunny yellow shirt, denim overalls, and red rain boots.",
    personality: "Creative, caring, and brave." },
  { name: "Bop the Robot", kind: "robot", color: "#76b8c5", accent: "#b6f0dd",
    description: "A friendly little robot who likes solving puzzles.",
    appearance: "A small rounded sky-blue robot with a brushed metal body, glowing mint eyes, softly lit antenna, rounded hands, and a yellow chest star.",
    personality: "Helpful, thoughtful, and playful." },
  { name: "Fern the Dinosaur", kind: "dinosaur", color: "#74ad78", accent: "#f1ce82",
    description: "A young dinosaur learning to be a good friend.",
    appearance: "A little leafy-green dinosaur with a softly scaled back, warm golden belly, small amber back plates, bright curious eyes, and short sturdy legs.",
    personality: "Bold, funny, and kind." },
  { name: "Pip the Penguin", kind: "penguin", color: "#4c6689", accent: "#f5dc9c",
    description: "A brave penguin who loves exploring snowy places.",
    appearance: "A small charcoal-and-white penguin with a soft feathered look, rounded belly, bright black eyes, golden beak, and a coral knitted scarf.",
    personality: "Adventurous, upbeat, and caring." },
];

const appearanceKinds: [RegExp, string][] = [
  [/\bfox\b/i, "fox"], [/\brabbit|\bbunny|\bhare\b/i, "rabbit"], [/\bperson|\bgirl|\bboy|\bchild|\bhuman\b/i, "human"],
  [/\brobot\b/i, "robot"], [/\bdinosaur|\bdino\b/i, "dinosaur"], [/\bpenguin\b/i, "penguin"],
];

function characterKind(character: Character): string {
  const kind = appearanceKinds.find(([pattern]) => pattern.test(`${character.name} ${character.appearance}`))?.[1];
  return kind ?? "human";
}

function characterColors(character: Character, kind: string) {
  const preset = presets.find((item) => item.name === character.name);
  if (preset) return { color: preset.color, accent: preset.accent };
  const text = `${character.name} ${character.appearance}`.toLowerCase();
  const colors: Record<string, string> = {
    orange: "#e88343", red: "#c95c59", yellow: "#d9b64e", green: "#72a875",
    blue: "#6c91bd", purple: "#9b7bbb", pink: "#d58aa4", brown: "#986e54",
    black: "#57545a", white: "#ddd9d1", gray: "#a6a5a4", grey: "#a6a5a4",
  };
  const color = Object.entries(colors).find(([name]) => new RegExp(`\\b${name}\\b`).test(text))?.[1]
    ?? (kind === "fox" ? "#e88343" : kind === "rabbit" ? "#d9c8ef" : "#76a9bf");
  return { color, accent: "#f8dfb4" };
}

function CharacterPortrait({ kind, color, accent }: { kind: string; color: string; accent: string }) {
  const id = useId().replaceAll(":", "");
  return <svg className={`character-portrait portrait-${kind}`} viewBox="0 0 120 120" role="img" aria-label={`${kind} character illustration`}>
    <defs>
      <linearGradient id={`body-${id}`} x1="0" y1="0" x2="1" y2="1">
        <stop stopColor={accent} /><stop offset="1" stopColor={color} />
      </linearGradient>
      <radialGradient id={`shine-${id}`} cx=".35" cy=".25" r=".8">
        <stop stopColor="#fff" stopOpacity=".72" /><stop offset="1" stopColor="#fff" stopOpacity="0" />
      </radialGradient>
    </defs>
    <ellipse cx="60" cy="105" rx="33" ry="7" fill="#39304a" opacity=".11" />
    {kind === "rabbit" && <g><path d="M39 49 33 12q-1-7 5-5l18 38M68 45 76 9q2-7 7-2l1 39" fill={`url(#body-${id})`} stroke={color} strokeWidth="3" />
      <path d="m39 37-2-22 11 25m27-4 5-23 2 24" fill={accent} opacity=".9" /></g>}
    {kind === "fox" && <path d="M33 49 27 22l22 12 11-8 12 8 21-12-5 29" fill={`url(#body-${id})`} stroke={color} strokeWidth="3" strokeLinejoin="round" />}
    {kind === "dinosaur" && <path d="m35 55 3-13 10 10 5-17 11 15 8-11 9 18" fill={accent} stroke={color} strokeWidth="2" />}
    {kind === "human" && <g fill="#302639"><circle cx="42" cy="31" r="16" /><circle cx="69" cy="28" r="17" /><circle cx="80" cy="42" r="12" /></g>}
    {kind === "robot" && <g fill={color} stroke="#477f95" strokeWidth="3" strokeLinejoin="round">
      <path d="M60 29V17m0 0-8-6m8 6 8-6" fill="none" /><circle cx="60" cy="9" r="4" fill={accent} />
      <rect x="30" y="29" width="60" height="54" rx="18" /><rect x="26" y="84" width="19" height="13" rx="6" /><rect x="75" y="84" width="19" height="13" rx="6" />
    </g>}
    {kind !== "robot" && <g>
      <path d="M34 65q0-29 26-29t26 29v26q-26 20-52 0Z" fill={`url(#body-${id})`} stroke={color} strokeWidth="2" />
      <path d="M38 59q3-19 22-19t22 19q-22-9-44 0" fill={`url(#shine-${id})`} />
      {kind === "human" && <path d="M36 75q24 15 48 0v17q-24 17-48 0Z" fill="#e8ad66" />}
      {kind === "penguin" && <ellipse cx="60" cy="72" rx="17" ry="25" fill="#f7f3e9" />}
      {kind === "fox" && <path d="M47 73q13-12 26 0l-13 11Z" fill="#fff2d8" />}
      {kind === "dinosaur" && <ellipse cx="60" cy="75" rx="16" ry="20" fill="#e7ca86" />}
      {kind === "rabbit" && <ellipse cx="60" cy="78" rx="15" ry="17" fill="#f5f0eb" />}
    </g>}
    {kind === "robot" ? <g><rect x="38" y="39" width="44" height="29" rx="12" fill="#233c52" />
      <ellipse cx="49" cy="52" rx="4" ry="6" fill={accent} /><ellipse cx="71" cy="52" rx="4" ry="6" fill={accent} />
      <path d="M52 62q8 5 16 0" fill="none" stroke={accent} strokeWidth="2" /></g> :
      <g>
        <ellipse cx="49" cy="59" rx="7" ry="9" fill="#fff" /><ellipse cx="71" cy="59" rx="7" ry="9" fill="#fff" />
        <ellipse cx="50" cy="60" rx="3.5" ry="5.5" fill="#493d48" /><ellipse cx="70" cy="60" rx="3.5" ry="5.5" fill="#493d48" />
        <circle cx="51" cy="58" r="1.5" fill="#fff" /><circle cx="71" cy="58" r="1.5" fill="#fff" />
        {kind === "fox" || kind === "rabbit" ? <path d="m56 69 4 3 4-3" fill="#d98282" /> : <path d="M53 73q7 6 14 0" fill="none" stroke="#704950" strokeWidth="2" strokeLinecap="round" />}
      </g>}
    {kind === "human" && <path d="M39 45q5-12 15-12 8 0 13 8-13-4-28 4" fill="#302639" />}
    {kind === "fox" && <path d="M80 82q21-6 22 10-5 17-23 4" fill={`url(#body-${id})`} stroke={color} strokeWidth="3" />}
    {kind === "penguin" && <path d="m52 94-6 5m22-5 6 5" stroke="#e8a94f" strokeWidth="5" strokeLinecap="round" />}
    <ellipse cx="47" cy="47" rx="18" ry="10" fill={`url(#shine-${id})`} />
  </svg>;
}

export function CharacterStudio({ selectedIds, onSelectionChange, onCreateStory }: {
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onCreateStory: () => void;
}) {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [appearance, setAppearance] = useState("");
  const [personality, setPersonality] = useState("");

  useEffect(() => {
    let current = true;
    api.listCharacters().then((items) => { if (current) setCharacters(items); })
      .catch((err: unknown) => { if (current) setError(err instanceof ApiError ? err.message : "Could not load characters."); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, []);

  const add = async (profile: CharacterCreateRequest): Promise<boolean> => {
    if (selectedIds.length >= 10) {
      setError("Select up to 10 characters for one story.");
      return false;
    }
    setSaving(true);
    setError("");
    try {
      const created = await api.createCharacter(profile);
      setCharacters((current) => [...current, created]);
      if (!selectedIds.includes(created.id)) onSelectionChange([...selectedIds, created.id]);
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save this character.");
      return false;
    } finally {
      setSaving(false);
    }
  };

  async function createCustom(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (await add({ name: name.trim(), description: "", appearance: appearance.trim(), personality: personality.trim() })) {
      setName("");
      setAppearance("");
      setPersonality("");
    }
  }

  const toggle = (id: string) => {
    if (selectedIds.includes(id)) onSelectionChange(selectedIds.filter((item) => item !== id));
    else if (selectedIds.length < 10) onSelectionChange([...selectedIds, id]);
    else setError("Select up to 10 characters for one story.");
  };

  return <section className="character-studio">
    <div className="page-title-row">
      <div><div className="eyebrow"><span className="eyebrow-line" /> YOUR CAST</div>
        <h1>Character Studio</h1>
        <p>Choose a character style and save your cast for the next story.</p></div>
      <button className="primary-button" onClick={onCreateStory}>Create a story <Icon name="arrow" /></button>
    </div>
    <div className="character-note"><Icon name="spark" /><span>These are detailed, locally drawn cartoon characters, not photorealistic or AI-generated images. Saved character choices are used when you create a new story.</span></div>
    {error && <div className="alert-banner error-banner" role="alert"><Icon name="alert" />{error}</div>}
    <section className="character-section">
      <div className="character-section-title"><div><h2>Starter characters</h2><p>Save any character to your library; selected ones join your next story.</p></div></div>
      <div className="character-grid">
        {presets.map((profile) => {
          const saved = characters.some((character) => character.name === profile.name);
          return <article className="character-card starter-card" key={profile.name}>
            <div className={`character-art art-${profile.kind}`}><CharacterPortrait kind={profile.kind} color={profile.color} accent={profile.accent} />
              <span className="character-style-tag">Illustrated</span></div>
            <div className="character-card-copy"><h3>{profile.name}</h3><p>{profile.description}</p>
              <span className="character-trait">{profile.personality}</span>
              <button className="secondary-button character-action" disabled={saving || saved}
                onClick={() => void add(profile)}>{saved ? <><Icon name="check" /> In your library</> : <><Icon name="plus" /> Add character</>}</button>
            </div>
          </article>;
        })}
      </div>
    </section>
    <section className="character-section">
      <div className="character-section-title"><div><h2>My characters</h2>
        <p>{selectedIds.length} selected for your next story</p></div></div>
      {loading ? <div className="empty-card">Loading your character library...</div> : characters.length ? <div className="character-grid">
        {characters.map((character) => {
          const kind = characterKind(character);
          const theme = characterColors(character, kind);
          return <label className={`character-card library-card ${selectedIds.includes(character.id) ? "selected" : ""}`} key={character.id}>
            <div className={`character-art art-${kind}`}><CharacterPortrait kind={kind} color={theme.color} accent={theme.accent} />
              <span className="character-style-tag">{selectedIds.includes(character.id) ? "Selected" : "Your character"}</span></div>
            <div className="character-card-copy"><h3>{character.name}</h3><p>{character.appearance}</p>
              {character.personality && <span className="character-trait">{character.personality}</span>}
              <span className="character-pick"><input type="checkbox" checked={selectedIds.includes(character.id)}
                onChange={() => toggle(character.id)} /> Use in next story</span>
            </div>
          </label>;
        })}
      </div> : <div className="empty-card">Add a starter character or create your own to begin your library.</div>}
    </section>
    <section className="character-section custom-character-section">
      <div className="character-section-title"><div><h2>Create a character</h2><p>Describe their appearance so scenes can match their design.</p></div></div>
      <form className="character-form" onSubmit={(event) => void createCustom(event)}>
        <label className="field"><span>Character name</span><input required maxLength={80} value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Kavi the tiger" /></label>
        <label className="field"><span>Appearance</span><textarea required maxLength={1000} value={appearance} onChange={(event) => setAppearance(event.target.value)} placeholder="Fur, colours, eyes, clothing, distinctive features..." /></label>
        <label className="field"><span>Personality <small>optional</small></span><input maxLength={500} value={personality} onChange={(event) => setPersonality(event.target.value)} placeholder="Curious, gentle, and brave" /></label>
        <button className="primary-button" disabled={saving}>{saving ? "Saving..." : <>Save character <Icon name="plus" /></>}</button>
      </form>
    </section>
  </section>;
}
