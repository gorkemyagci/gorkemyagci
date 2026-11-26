// Draws the contribution heatmap as two SVGs (light and dark) in the
// Record style: a strict square grid, no rounded corners, ink greys only.
//
// Usage
//   GH_TOKEN=... GH_LOGIN=gorkemyagci node scripts/heatmap.mjs
//   node scripts/heatmap.mjs --sample   (fake data, for previews only)
//
// No dependencies. Needs Node 20+ for global fetch.

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const font = JSON.parse(await readFile(join(here, "heatmap-glyphs.json"), "utf8"));

const LEVELS = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"];

const THEMES = {
  light: {
    ink: "#0b0b0c",
    muted: "#5c5c5c",
    line: "#e4e4e2",
    cells: ["#f0f0ee", "#cfcfcc", "#9a9a97", "#5c5c5c", "#0b0b0c"],
  },
  dark: {
    ink: "#f0f0ee",
    muted: "#9a9a97",
    line: "#2a2e35",
    cells: ["#161b22", "#3d424a", "#6e7178", "#a9aaa8", "#f0f0ee"],
  },
};

// Geometry. 53 columns at a 16px pitch fill the 860px README width.
const W = 860;
const CELL = 12;
const PITCH = 16;
const TOP = 0.5; // top rule
const HEAD_BASE = 34; // baseline of the count and legend row
const MONTH_BASE = 66; // baseline of the month labels
const GRID_Y = 80;
const H = GRID_Y + 7 * PITCH - (PITCH - CELL) + 24.5;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function textWidth(str, size) {
  const s = size / font.upem;
  let w = 0;
  for (const ch of str) w += (font.glyphs[ch]?.a ?? 0) * s;
  return w;
}

function text(str, size, x, y, fill) {
  const s = size / font.upem;
  let cx = x;
  let out = "";
  for (const ch of str) {
    const g = font.glyphs[ch];
    if (!g) continue;
    if (g.d) {
      out += `<path transform="translate(${cx.toFixed(2)} ${y}) scale(${s.toFixed(5)} ${(-s).toFixed(5)})" d="${g.d}"/>`;
    }
    cx += g.a * s;
  }
  return `<g fill="${fill}">${out}</g>`;
}

async function fetchCalendar(login, token) {
  const query = `query($login: String!) {
    user(login: $login) {
      contributionsCollection {
        contributionCalendar {
          totalContributions
          weeks { contributionDays { date weekday contributionCount contributionLevel } }
        }
      }
    }
  }`;
  const res = await fetch("https://api.github.com/graphql", {
    method: "POST",
    headers: { Authorization: `bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ query, variables: { login } }),
  });
  if (!res.ok) throw new Error(`GitHub API ${res.status}`);
  const json = await res.json();
  if (json.errors) throw new Error(JSON.stringify(json.errors));
  return json.data.user.contributionsCollection.contributionCalendar;
}

function sampleCalendar() {
  // Deterministic fake data so previews are stable. Never committed as real.
  let seed = 7;
  const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const end = new Date(Date.UTC(2026, 10, 26));
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - 364 - end.getUTCDay());
  const weeks = [];
  let total = 0;
  for (let d = new Date(start); d <= end; d.setUTCDate(d.getUTCDate() + 1)) {
    if (d.getUTCDay() === 0) weeks.push({ contributionDays: [] });
    const busy = d.getUTCDay() % 6 !== 0 ? 0.78 : 0.35;
    const r = rand();
    const level = r > busy ? 0 : Math.min(4, 1 + Math.floor(rand() * rand() * 5));
    const count = level === 0 ? 0 : level * 3 + Math.floor(rand() * 3);
    total += count;
    weeks.at(-1).contributionDays.push({
      date: d.toISOString().slice(0, 10),
      weekday: d.getUTCDay(),
      contributionCount: count,
      contributionLevel: LEVELS[level],
    });
  }
  return { totalContributions: total, weeks };
}

function render(cal, theme) {
  const c = THEMES[theme];
  const weeks = cal.weeks.slice(-53);
  const gridW = weeks.length * PITCH - (PITCH - CELL);
  const x0 = 0;
  const parts = [];

  parts.push(`<path d="M0 ${TOP}H${W}M0 ${H - 0.5}H${W}" stroke="${c.line}" stroke-width="1"/>`);

  const count = `${cal.totalContributions.toLocaleString("en-US")} contributions in the last year`;
  parts.push(text(count, 13, x0, HEAD_BASE, c.muted));

  // Legend, right aligned to the grid edge.
  const less = "Less";
  const more = "More";
  const legendCells = 5 * PITCH - (PITCH - CELL);
  const moreX = x0 + gridW - textWidth(more, 12);
  const cellsX = moreX - 8 - legendCells;
  const lessX = cellsX - 8 - textWidth(less, 12);
  parts.push(text(less, 12, lessX, HEAD_BASE, c.muted));
  c.cells.forEach((fill, i) => {
    parts.push(`<rect x="${cellsX + i * PITCH}" y="${HEAD_BASE - 10}" width="${CELL}" height="${CELL}" fill="${fill}"/>`);
  });
  parts.push(text(more, 12, moreX, HEAD_BASE, c.muted));

  // Month labels on the first full week of each month; skip one that
  // would sit closer than three columns to the previous label.
  let lastCol = -10;
  let lastMonth = -1;
  weeks.forEach((w, col) => {
    const first = w.contributionDays[0];
    if (!first) return;
    const m = new Date(first.date + "T00:00:00Z").getUTCMonth();
    if (m !== lastMonth) {
      if (col - lastCol >= 3 && !(col === 0 && w.contributionDays.length < 7)) {
        parts.push(text(MONTHS[m], 12, x0 + col * PITCH, MONTH_BASE, c.muted));
        lastCol = col;
      }
      lastMonth = m;
    }
  });

  // Grid. Every cell sits on the same pitch; missing days stay empty.
  const cells = [];
  weeks.forEach((w, col) => {
    for (const d of w.contributionDays) {
      const level = Math.max(0, LEVELS.indexOf(d.contributionLevel));
      const x = x0 + col * PITCH;
      const y = GRID_Y + d.weekday * PITCH;
      const label = `${d.date}: ${d.contributionCount}`;
      cells.push(`<rect x="${x}" y="${y}" width="${CELL}" height="${CELL}" fill="${c.cells[level]}"><title>${label}</title></rect>`);
    }
  });
  parts.push(`<g shape-rendering="crispEdges">${cells.join("")}</g>`);

  const title = `GitHub contributions, ${count}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${title}"><title>${title}</title>${parts.join("")}</svg>\n`;
}

const sample = process.argv.includes("--sample");
const login = process.env.GH_LOGIN;
const token = process.env.GH_TOKEN;
if (!sample && (!login || !token)) {
  console.error("Set GH_LOGIN and GH_TOKEN, or pass --sample.");
  process.exit(1);
}

const cal = sample ? sampleCalendar() : await fetchCalendar(login, token);
const outDir = join(root, "assets");
await mkdir(outDir, { recursive: true });
await writeFile(join(outDir, "heatmap-light.svg"), render(cal, "light"));
await writeFile(join(outDir, "heatmap-dark.svg"), render(cal, "dark"));
console.log(`heatmap: ${cal.totalContributions} contributions${sample ? " (sample)" : ""}`);
