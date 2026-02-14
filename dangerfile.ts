import { danger, warn, fail, message, markdown } from "danger";

const modifiedFiles = danger.git.modified_files;
const createdFiles = danger.git.created_files;
const deletedFiles = danger.git.deleted_files;
const allChangedFiles = [...modifiedFiles, ...createdFiles];
const linesChanged =
  (danger.github.pr.additions ?? 0) + (danger.github.pr.deletions ?? 0);

// ─── PR Size ────────────────────────────────────────────────────────────────
if (linesChanged > 500) {
  warn(
    `This PR has **${linesChanged} lines** changed. Consider breaking it into smaller PRs for easier review.`
  );
}

// ─── PR Description ─────────────────────────────────────────────────────────
if ((danger.github.pr.body?.trim() ?? "").length < 10) {
  warn(
    "Please add a meaningful PR description so reviewers understand the context."
  );
}

// ─── Requirements Changed ───────────────────────────────────────────────────
if (modifiedFiles.includes("requirements.txt")) {
  message("`requirements.txt` was updated — make sure dependencies are tested.");
}

// ─── Sensitive Files ────────────────────────────────────────────────────────
const sensitivePatterns = [".env", "credentials", "secret"];
const sensitiveFiles = allChangedFiles.filter((f) =>
  sensitivePatterns.some(
    (p) => f.toLowerCase().includes(p) && !f.includes("example") && !f.includes("sample")
  )
);
if (sensitiveFiles.length > 0) {
  fail(
    `**Sensitive files modified — review carefully:**\n${sensitiveFiles.map((f) => `- \`${f}\``).join("\n")}`
  );
}

// ─── CI/CD Config Changes ───────────────────────────────────────────────────
const ciFiles = allChangedFiles.filter(
  (f) => f.includes(".github/workflows") || f === "Dockerfile" || f === "docker-compose.yml"
);
if (ciFiles.length > 0) {
  message(
    `**CI/CD or infrastructure files changed:**\n${ciFiles.map((f) => `- \`${f}\``).join("\n")}`
  );
}

// ─── Python-Specific Checks ─────────────────────────────────────────────────
const pyFiles = allChangedFiles.filter(
  (f) => f.endsWith(".py") && !f.includes("__pycache__") && !f.includes("migrations")
);

const checkForPatterns = async () => {
  for (const file of pyFiles) {
    const diff = await danger.git.diffForFile(file);
    if (!diff) continue;
    const added = diff.added;

    if (/\bprint\s*\(/.test(added)) {
      warn(`\`${file}\` has \`print()\` statements — consider using \`logging\` instead.`);
    }
    if (/\bbreakpoint\s*\(/.test(added) || /\bpdb\.set_trace\s*\(/.test(added)) {
      fail(`\`${file}\` has a debugger breakpoint — remove before merging.`);
    }
    if (/import\s+pdb/.test(added)) {
      fail(`\`${file}\` imports \`pdb\` — remove before merging.`);
    }
    if (/#\s*(TODO|FIXME|HACK|XXX)\b/i.test(added)) {
      message(`\`${file}\` has new TODO/FIXME comments — make sure these are tracked.`);
    }
  }
};

// ─── Migration Files ────────────────────────────────────────────────────────
const migrationFiles = allChangedFiles.filter((f) => f.includes("migrations/"));
if (migrationFiles.length > 0) {
  message(
    `**Database migration files changed:**\n${migrationFiles.map((f) => `- \`${f}\``).join("\n")}\nMake sure these are reviewed carefully.`
  );
}

// ─── Deleted Files ──────────────────────────────────────────────────────────
if (deletedFiles.length > 5) {
  message(`**${deletedFiles.length} files deleted** — make sure nothing important was removed.`);
}

// ─── Summary Table ──────────────────────────────────────────────────────────
markdown(`### PR Stats
| Metric | Count |
|--------|-------|
| Files Changed | ${modifiedFiles.length} |
| Files Added | ${createdFiles.length} |
| Files Deleted | ${deletedFiles.length} |
| Lines Added | +${danger.github.pr.additions} |
| Lines Removed | -${danger.github.pr.deletions} |
`);

checkForPatterns();
