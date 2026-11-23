// What the admin may edit. Only information text: guides, rule and source texts, pack texts and page paragraphs.
// Generated files are left out, because the build overwrites them.

// YAML keys that hold information text. Keys such as label, button, id, level or pattern are never editable.
export const TEXT_KEYS = /^(title|requirement|rationale|improvement|notes?|status|summary|description|desc|help|intro|text|target|why|look_for|ideas|question|meaning|asks|aspect|csef_note|watch|effect|hero_title|lead(_[a-z]+)?|get\d+_d)$/;

export const SITES = {
  csef: {
    name: "CSEF",
    title: "Child-Safe EdTech Framework",
    repo: "eduardon83/child-safe-edtech-framework",
    branch: "main",
    site: "https://csef.kendirstudios.pt",
    files: [
      { glob: "README.md", kind: "markdown", group: "Guides" },
      { glob: "framework/*.md", kind: "markdown", group: "Guides" },
      { glob: "framework/rules.yaml", kind: "yaml", group: "Rules and sources" },
      { glob: "framework/sources.yaml", kind: "yaml", group: "Rules and sources" },
      { glob: "packs/*.yaml", kind: "yaml", group: "Packs", exclude: ["packs/_template.yaml"] },
      { glob: "framework/compass/targets.yaml", kind: "yaml", group: "Literacy Compass" },
      { glob: "framework/serious-games/criteria.yaml", kind: "yaml", group: "Labels" },
      { glob: "framework/questionnaire.yaml", kind: "yaml", group: "Questionnaire" },
      { glob: "framework/i18n/*.yaml", kind: "yaml", group: "Questionnaire translations" },
      { glob: "tooling/*.template.html", kind: "html", group: "Page text" },
    ],
  },
  hdsf: {
    name: "HDSF",
    title: "Health Data Safety Framework",
    repo: "eduardon83/digital-health-safety-framework",
    branch: "main",
    site: "https://hdsf.kendirstudios.pt",
    files: [
      { glob: "README.md", kind: "markdown", group: "Guides" },
      { glob: "framework/*.md", kind: "markdown", group: "Guides", exclude: ["framework/legislation.md", "framework/gdpr-map.md"] },
      { glob: "framework/rules.yaml", kind: "yaml", group: "Rules and sources" },
      { glob: "framework/sources.yaml", kind: "yaml", group: "Rules and sources" },
      { glob: "framework/watch.yaml", kind: "yaml", group: "Rules and sources" },
      { glob: "packs/*.yaml", kind: "yaml", group: "Packs", exclude: ["packs/_template.yaml"] },
      { glob: "tooling/home.template.html", kind: "html", group: "Page text" },
      { glob: "tooling/workbench.template.html", kind: "html", group: "Page text" },
    ],
  },
};

// Friendly names for files whose name says little.
export const NAMES = {
  "README.md": "Read me (GitHub front page)",
  "tooling/landing.template.html": "Home page",
  "tooling/home.template.html": "Home page",
  "tooling/workbench.template.html": "Workbench page",
  "tooling/pack-builder.template.html": "Pack Builder page",
  "tooling/submit.template.html": "Submit a label package page",
};

function globRe(glob) {
  return new RegExp("^" + glob.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, "[^/]*") + "$");
}

// The rule for a path, or null when the path may not be edited.
export function ruleFor(site, path) {
  if (typeof path !== "string" || path.includes("..") || path.startsWith("/")) return null;
  for (const f of site.files) {
    if (globRe(f.glob).test(path) && !(f.exclude || []).includes(path)) return f;
  }
  return null;
}
