import fs from 'node:fs';
import process from 'node:process';

/**
 * Write JSON through a temp file + rename, so a reader never observes a
 * half-written file and a crash mid-write cannot truncate the original.
 */
export function atomicWriteJson(file: string, value: unknown): void {
  const tmp = `${file}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tmp, `${JSON.stringify(value, null, 2)}\n`, 'utf-8');
  fs.renameSync(tmp, file);
}
