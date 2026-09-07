import { createPinia, type Pinia } from 'pinia';
import { createApp } from 'vue';
import { StoreResetPlugin } from '@/modules/shell/app/store-plugins';

/**
 * A pinia carrying the plugins the application installs, whether or not the spec mounts anything.
 *
 * @remarks
 * `pinia.use()` only queues a plugin: `install(app)` is what moves it into the active list, and that
 * runs on `app.use(pinia)`. A spec that calls `setActivePinia(createCustomPinia())` and never mounts
 * therefore ran with no plugins at all, so `$reset` stayed pinia's setup-store version, which throws
 * in development and does nothing in a production build. Installing into a throwaway app here makes
 * the helper mean what its name says.
 *
 * Mounting with `global: { plugins: [pinia] }` installs again, which re-points pinia at the test's
 * own app; the plugin list is already drained by then, so nothing is registered twice.
 *
 * @returns a pinia with `StoreResetPlugin` applied to every store it creates
 */
export function createCustomPinia(): Pinia {
  const pinia = createPinia();
  pinia.use(StoreResetPlugin);
  createApp({}).use(pinia);

  return pinia;
}
