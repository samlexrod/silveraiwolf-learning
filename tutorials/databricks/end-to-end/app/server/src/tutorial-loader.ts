import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { TutorialConfig } from "./tutorial-types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = join(__dirname, "../data/tutorials");

const cache = new Map<string, TutorialConfig>();

export function loadTutorial(id: string): TutorialConfig {
  if (cache.has(id)) return cache.get(id)!;
  const path = join(DATA_DIR, `${id}.json`);
  const config = JSON.parse(readFileSync(path, "utf-8")) as TutorialConfig;
  cache.set(id, config);
  return config;
}

/** All tutorial IDs available on disk — for future marketplace listing */
export function listTutorialIds(): string[] {
  try {
    return readdirSync(DATA_DIR)
      .filter((f) => f.endsWith(".json"))
      .map((f) => f.replace(/\.json$/, ""));
  } catch {
    return [];
  }
}

/** The default tutorial for the current app */
export function defaultTutorial(): TutorialConfig {
  return loadTutorial("databricks-end-to-end");
}
