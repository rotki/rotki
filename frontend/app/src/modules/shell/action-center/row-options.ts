import type { ActionItemOption, ActionTarget } from '@/modules/core/action-center/types';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { SettingsCategoryIds } from '@/modules/settings/setting-highlight-ids';

/** The indexer order in the chain settings, where a missing indexer or an indexer's key is dealt with. */
export const INDEXER_SETTINGS: ActionTarget = {
  highlight: SettingsCategoryIds.INDEXER,
  kind: 'route',
  to: { name: '/settings/chains/' },
};

interface SuppressOptionDefinition {
  label: string;
  confirmTitle: string;
  confirmMessage: string;
  /** writes the setting that keeps this row from being raised again */
  suppress: () => Promise<void>;
}

interface UseSuppressOptionReturn {
  suppressOption: (definition: SuppressOptionDefinition) => ActionItemOption;
}

/**
 * Builds the "do not show again" option, which asks before it writes.
 *
 * @remarks
 * The setting it writes is also what hides the row, so the row leaves on its own once the write lands.
 */
export function useSuppressOption(): UseSuppressOptionReturn {
  const { show } = useConfirmStore();

  function suppressOption({ confirmMessage, confirmTitle, label, suppress }: SuppressOptionDefinition): ActionItemOption {
    return {
      danger: true,
      icon: 'lu-bell-off',
      id: 'do-not-show-again',
      label,
      target: {
        kind: 'run',
        run: () => show({ message: confirmMessage, title: confirmTitle }, suppress),
      },
    };
  }

  return { suppressOption };
}
