import type { Ref } from 'vue';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';

interface UseActionCenterFoldsReturn {
  /** ids of the sections the user folded, bound with `v-model` */
  modelFolded: Ref<string[]>;
}

/**
 * Which action center sections the user folded away, kept per user in local storage.
 *
 * @remarks
 * A folded section stays folded when a new row arrives in it: the header says so instead, since a
 * section that opens by itself moves everything under it while the user is reading.
 */
export function useActionCenterFolds(): UseActionCenterFoldsReturn {
  const userId = useLoggedUserIdentifier();

  const modelFolded: Ref<string[]> = useLocalStorage<string[]>(() => `${get(userId)}.rotki_action_center_folded`, []);

  return { modelFolded };
}
