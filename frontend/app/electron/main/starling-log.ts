import type { LogService } from '@electron/main/log-service';
import { LogLevel } from '@shared/log-level';

/**
 * starling emits tracing-formatted stderr: `<ISO timestamp>  <LEVEL> <target>: <msg>`,
 * often with ANSI coloring around the timestamp and level. We strip the ANSI, parse
 * the real level (so the log badge matches) and drop the duplicate timestamp. Lines
 * that do not match (e.g. the inherited backend stderr) are forwarded as-is.
 */
// Matches ANSI SGR sequences (ESC [ ... m) without embedding a control char in source.
const ANSI_PATTERN = new RegExp(`${String.fromCharCode(27)}\\[[0-9;]*m`, 'g');
const STARLING_LOG_LINE = /^\d{4}-\d{2}-\d{2}[T ][\d:.]+Z?\s+(TRACE|DEBUG|INFO|WARN|ERROR)\s+(.*)$/;
const STARLING_LEVELS: Record<string, LogLevel> = {
  TRACE: LogLevel.TRACE,
  DEBUG: LogLevel.DEBUG,
  INFO: LogLevel.INFO,
  WARN: LogLevel.WARNING,
  ERROR: LogLevel.ERROR,
};

/** Forward one starling stderr line to the electron log under the `[starling]` marker. */
export function forwardStarlingLine(logger: LogService, line: string): void {
  const clean = line.replace(ANSI_PATTERN, '');
  const match = STARLING_LOG_LINE.exec(clean);
  const level = match ? STARLING_LEVELS[match[1]] ?? logger.getLogLevel() : logger.getLogLevel();
  const text = match ? match[2] : clean;
  logger.write(level, `[starling] ${text}`);
}
