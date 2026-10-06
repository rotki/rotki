import { startPromise } from '@shared/utils';
import { hasLiveSession, onPendingWrite } from '@/modules/core/session/session-lifecycle';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useFrontendSettingsWriter } from '@/modules/settings/use-frontend-settings-writer';

const PERSIST_DEBOUNCE_MS = 800;
const PERSIST_MAX_WAIT_MS = 1200;

/**
 * Persists the rows-per-page choice made in any table, once for the whole app.
 *
 * @remarks
 * Tables write the shared {@link useItemsPerPage} ref directly, and the settings repo pushes the
 * stored value into it at login and after every write. A value the stored setting already holds
 * is that push, not a choice, and is not written back. The write is debounced; a logout runs a
 * pending one before it ends the session, and one still scheduled after that is dropped.
 */
export const useItemsPerPageWriter = createSharedComposable((): void => {
  const itemsPerPage = useItemsPerPage();
  const repo = useSettingsRepo();
  const { updateFrontendSetting } = useFrontendSettingsWriter();

  async function persist(): Promise<void> {
    const value = get(itemsPerPage);
    if (!hasLiveSession() || value === repo.frontend.itemsPerPage)
      return;

    await updateFrontendSetting({ itemsPerPage: value });
  }

  const schedule = useDebounceFn(persist, PERSIST_DEBOUNCE_MS, { maxWait: PERSIST_MAX_WAIT_MS });

  watch(itemsPerPage, () => startPromise(schedule()));
  tryOnScopeDispose(onPendingWrite('items-per-page', persist));
});
