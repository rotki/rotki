import process from 'node:process';
import { isatty } from 'node:tty';
import { stripVTControlCharacters } from 'node:util';

/**
 * Shared logger for the `pnpm dev` / `pnpm dev:web` run path (start-dev + its dev/
 * and dev-instance/ helpers) and for forwarding child-process output. Every line is
 * formatted as `<label> <time> <message>` so the orchestrator's own logs and the
 * forwarded child logs read the same. The timestamp uses the local 12-hour clock,
 * e.g. "2:21:05 PM".
 *
 * Child labels carry a reserved color (app/backend/colibri/proxy) and are passed to
 * formatDevLine directly. The orchestrator's own tags go through createDevLogger,
 * which paints them a single shared color so they are visually distinct from the
 * reserved child labels. When {@link useColor} is off, formatDevLine strips every
 * escape sequence from the finished line, so labels and child output come out plain.
 */

function resolveColor(env: NodeJS.ProcessEnv, isTTY: boolean): boolean {
  if (env.NO_COLOR)
    return false;
  if (env.FORCE_COLOR !== undefined)
    return env.FORCE_COLOR !== '0' && env.FORCE_COLOR !== 'false';
  return isTTY;
}

/**
 * Whether dev output carries ANSI color.
 *
 * @remarks
 * On for a terminal, off when stdout is redirected to a file or a pipe, so captured
 * logs stay greppable. `NO_COLOR` (non-empty) turns it off and `FORCE_COLOR` forces
 * it on, or off with `0`/`false`.
 */
export const useColor = resolveColor(process.env, isatty(process.stdout.fd));

// ESC-based regexes built without embedding a control char in source.
const ESC = String.fromCharCode(27);
const ANSI_GLOBAL = new RegExp(`${ESC}\\[[0-9;]*m`, 'g');
const ANSI_AT_START = new RegExp(`^${ESC}\\[[0-9;]*m`);

// Blue: not white, and not one of the child-label colors red/green/yellow/magenta.
const TAG_COLOR = '\u{1B}[34m';
const RESET = '\u{1B}[0m';

function timestamp(): string {
  return new Date().toLocaleTimeString('en-US');
}

function render(args: unknown[]): string {
  return args
    .map((arg) => {
      if (typeof arg === 'string')
        return arg;
      if (arg instanceof Error)
        return arg.stack ?? arg.message;
      return JSON.stringify(arg);
    })
    .join(' ');
}

/** Visible width of a string, ignoring ANSI SGR sequences. */
function visibleWidth(text: string): number {
  return text.replace(ANSI_GLOBAL, '').length;
}

/** Index in `text` just past the first `width` visible chars, never splitting an ANSI sequence. */
function cutAtVisible(text: string, width: number): number {
  let visible = 0;
  let i = 0;
  while (i < text.length && visible < width) {
    const match = ANSI_AT_START.exec(text.slice(i));
    if (match) {
      i += match[0].length;
      continue;
    }
    i += 1;
    visible += 1;
  }
  return i;
}

/**
 * Hard-wrap `message` to the terminal width, indenting continuation lines by
 * `indent` visible columns so wrapped text lines up under the message (i.e. past
 * the `<tag> <time> ` prefix). ANSI-aware so color codes do not count toward width.
 */
function wrapMessage(message: string, indent: number, columns: number): string {
  const width = columns - indent;
  if (width <= 0)
    return message;
  const pad = ' '.repeat(indent);
  const out: string[] = [];
  for (const rawLine of message.split('\n')) {
    let line = rawLine;
    let first = true;
    while (visibleWidth(line) > width) {
      const cut = cutAtVisible(line, width);
      out.push((first ? '' : pad) + line.slice(0, cut));
      line = line.slice(cut);
      first = false;
    }
    out.push((first ? '' : pad) + line);
  }
  return out.join('\n');
}

export function formatDevLine(label: string, message: string): string {
  const prefix = `${label} ${timestamp()} `;
  const columns = process.stdout.columns ?? 0;
  const indent = visibleWidth(prefix);
  // Only wrap for a real terminal wide enough to leave room for the message.
  const body = columns > indent + 8 ? wrapMessage(message, indent, columns) : message;
  const line = `${prefix}${body}`;
  return useColor ? line : stripVTControlCharacters(line);
}

export interface DevLogger {
  log: (...args: unknown[]) => void;
  info: (...args: unknown[]) => void;
  success: (...args: unknown[]) => void;
  warn: (...args: unknown[]) => void;
  error: (...args: unknown[]) => void;
}

export function createDevLogger(label: string): DevLogger {
  const tag = `${TAG_COLOR}${label.replace(ANSI_GLOBAL, '')}${RESET}`;
  const toOut = (...args: unknown[]): void => {
    process.stdout.write(`${formatDevLine(tag, render(args))}\n`);
  };
  const toErr = (...args: unknown[]): void => {
    process.stderr.write(`${formatDevLine(tag, render(args))}\n`);
  };
  return { log: toOut, info: toOut, success: toOut, warn: toErr, error: toErr };
}
