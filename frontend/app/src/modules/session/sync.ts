export const SYNC_UPLOAD = 'upload';

export const SYNC_DOWNLOAD = 'download';
// eslint-disable-next-line unused-imports/no-unused-vars -- read only through `typeof SYNC_ACTIONS` below, which the rule does not count as a use
const SYNC_ACTIONS = [SYNC_DOWNLOAD, SYNC_UPLOAD] as const;

export type SyncAction = (typeof SYNC_ACTIONS)[number];
