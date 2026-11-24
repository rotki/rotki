import { z } from 'zod';

export const SYNC_UPLOAD = 'upload';

export const SYNC_DOWNLOAD = 'download';
// eslint-disable-next-line unused-imports/no-unused-vars -- read only through `typeof SYNC_ACTIONS` below, which the rule does not count as a use
const SYNC_ACTIONS = [SYNC_DOWNLOAD, SYNC_UPLOAD] as const;

export type SyncAction = (typeof SYNC_ACTIONS)[number];

/** The database backup stored on the rotki server. */
export const RemoteBackup = z.object({
  /** The hash a deletion names, so that a backup uploaded since is kept. */
  dataHash: z.string(),
  dataSize: z.number().nonnegative(),
  /** The last write of the database the backup was made from. */
  lastModifyTs: z.number(),
  uploadTs: z.number(),
});

export type RemoteBackup = z.infer<typeof RemoteBackup>;

export const RemoteBackupResponse = z.object({
  backup: RemoteBackup.nullable(),
});

export type RemoteBackupResponse = z.infer<typeof RemoteBackupResponse>;

export const RemoteBackupDeletion = z.object({
  premiumShouldSync: z.boolean(),
});

export type RemoteBackupDeletion = z.infer<typeof RemoteBackupDeletion>;
