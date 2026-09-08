import type { UserDbBackup } from '@/modules/session/backup';

export function getFilepath(db: UserDbBackup, directory: string): string {
  const file = `${db.time}_rotkehlchen_db_v${db.version}.backup`;
  return `${directory}${file}`;
}

/**
 * The last segment of a path, whichever separator it uses.
 *
 * @remarks
 * The paths reaching here are built by the backend, so on Windows they arrive with backslashes.
 * Normalising to forward slashes first means one search finds the last separator of either kind.
 */
export function getFilename(fullPath: string): string {
  const normalizedPath = fullPath.replace(/\\/g, '/');
  return normalizedPath.substring(normalizedPath.lastIndexOf('/') + 1);
}

function getPublicAssetImagePath(path: string): string {
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
