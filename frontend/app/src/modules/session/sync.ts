export const SYNC_UPLOAD = 'upload';

export const SYNC_DOWNLOAD = 'download';
// eslint-disable-next-line unused-imports/no-unused-vars
const SYNC_ACTIONS = [SYNC_DOWNLOAD, SYNC_UPLOAD] as const;

export type SyncAction = (typeof SYNC_ACTIONS)[number];
