import type { UserDbBackup } from '@/types/backup';
import type { Ref } from 'vue';

export function getFilepath(db: UserDbBackup, directory: Ref<string>): string {
  const file = `${db.time}_rotkehlchen_db_v${db.version}.backup`;
  return `${directory.value}${file}`;
}

export function getFilename(fullPath: string): string {
  // Replace all backslashes with forward slashes.
  const normalizedPath = fullPath.replace(/\\/g, '/');

  // Return the substring after the last forward slash.
  return normalizedPath.substring(normalizedPath.lastIndexOf('/') + 1);
}
