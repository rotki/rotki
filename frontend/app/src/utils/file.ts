import type { Ref } from 'vue';
import type { UserDbBackup } from '@/types/backup';

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

export function getPublicAssetImagePath(path: string): string {
  return `./assets/images/${path}`;
}

export function getPublicServiceImagePath(path: string): string {
  return getPublicAssetImagePath(`services/${path}`);
}

export function getPublicProtocolImagePath(path: string): string {
  return getPublicAssetImagePath(`protocols/${path}`);
}

export function getPublicPlaceholderImagePath(path: string): string {
  return getPublicAssetImagePath(`placeholder/${path}`);
}
