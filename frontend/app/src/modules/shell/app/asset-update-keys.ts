/**
 * Key holding the remote asset-database version the user chose to skip.
 *
 * @remarks
 * Read and written by every surface that can raise the update prompt, so that skipping it in one
 * keeps it away in the others and across restarts. Kept in a module of its own, with no imports of
 * its own, so the login flow and the app shell can both reach it without importing each other.
 */
export const SKIPPED_ASSET_VERSION_KEY = 'rotki_skip_asset_db_version';

/** Session key set by the app to suppress the asset-update check entirely for this run. */
export const SKIP_ASSET_UPDATE_KEY = 'skip_update';
