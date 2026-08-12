import fs from 'node:fs';
import path from 'node:path';
import * as z from 'zod/mini';

/**
 * The on-disk half of {@link PasswordManager}, replacing electron-store.
 *
 * electron-store cost ~230 KB of the main bundle, most of it ajv, pulled in for JSON-schema
 * validation we never asked for. What it actually gave us was a JSON file, so this keeps the file
 * and drops the dependency. Every default it applied is reproduced below, because an installed
 * client already has one of these files: `<userData>/config.json`, serialized exactly as conf did
 * (`JSON.stringify(value, undefined, '\t')`), written with mode 0o666.
 */

const CONFIG_FILE_MODE = 0o666;

/** Values are read as unknown so a legacy nested entry parses instead of throwing. */
const StoredPasswords = z.record(z.string(), z.unknown());

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

interface LoadedStore {
  entries: Record<string, string>;
  /** True when the file held dot-prop nesting that has been flattened and needs writing back. */
  legacy: boolean;
}

/**
 * conf wrote through dot-prop, so a username containing a dot landed as nested objects
 * (`john.doe` became `{ john: { doe: ... } }`) while every read here is a flat lookup. Those
 * entries were therefore unreachable: the password saved and never restored. Flattening rejoins
 * them with the dot, which both recovers them and matches how they are written from now on.
 */
function flatten(value: Record<string, unknown>, prefix = ''): LoadedStore {
  const entries: Record<string, string> = {};
  let legacy = false;

  for (const [key, entry] of Object.entries(value)) {
    const name = prefix ? `${prefix}.${key}` : key;
    if (typeof entry === 'string') {
      entries[name] = entry;
    }
    else if (isRecord(entry)) {
      const nested = flatten(entry, name);
      Object.assign(entries, nested.entries);
      legacy = true;
    }
  }

  return { entries, legacy };
}

export class PasswordStore {
  constructor(private readonly filePath: string) {}

  private load(): Record<string, string> {
    if (!fs.existsSync(this.filePath))
      return {};

    let loaded: LoadedStore;
    try {
      const file = fs.readFileSync(this.filePath, { encoding: 'utf8' });
      loaded = flatten(StoredPasswords.parse(JSON.parse(file)));
    }
    catch (error: any) {
      console.error(error, 'Could not read the password store');
      return {};
    }

    // Rewrite once so the nesting does not have to be understood again.
    if (loaded.legacy)
      this.write(loaded.entries);

    return loaded.entries;
  }

  private write(entries: Record<string, string>): void {
    const data = JSON.stringify(entries, undefined, '\t');
    const temporary = `${this.filePath}.tmp`;
    try {
      fs.mkdirSync(path.dirname(this.filePath), { recursive: true });
      // Written to a sibling and renamed, because a half-written file here loses every saved
      // password. This is what `atomically` did for us under electron-store.
      fs.writeFileSync(temporary, data, { encoding: 'utf8', mode: CONFIG_FILE_MODE });
      fs.renameSync(temporary, this.filePath);
    }
    catch (error: any) {
      console.error(error, 'Could not write the password store');
    }
  }

  get(key: string): string | undefined {
    return this.load()[key];
  }

  set(key: string, value: string): void {
    const entries = this.load();
    entries[key] = value;
    this.write(entries);
  }

  isEmpty(): boolean {
    return Object.keys(this.load()).length === 0;
  }

  clear(): void {
    this.write({});
  }
}
