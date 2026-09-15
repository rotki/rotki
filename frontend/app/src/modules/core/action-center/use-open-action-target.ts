import type { ActionTarget } from '@/modules/core/action-center/types';
import { startPromise } from '@shared/utils';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { useSettingsHighlight } from '@/modules/settings/use-settings-highlight';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

interface UseOpenActionTargetReturn {
  /**
   * Follows a target, and closes the center first unless the target acts in place.
   *
   * @param target - one of the targets every center understands
   * @param close - closes the center hosting the row
   */
  openTarget: (target: ActionTarget, close: () => void) => void;
}

/** Whether following a target takes the user somewhere else, so the center should close behind it. */
function leavesCenter(target: ActionTarget): boolean {
  return target.kind !== 'run';
}

/**
 * Resolves the targets every action center understands.
 *
 * @remarks
 * A center with targets of its own resolves those first and hands the rest here.
 */
export function useOpenActionTarget(): UseOpenActionTargetReturn {
  const router = useRouter();
  const { pinPanel } = useAreaVisibilityStore();
  const { openUrl } = useInterop();
  const { requestHighlight } = useSettingsHighlight();

  function openTarget(target: ActionTarget, close: () => void): void {
    if (leavesCenter(target))
      close();

    switch (target.kind) {
      case 'external':
        startPromise(openUrl(target.url));
        break;
      case 'pin':
        pinPanel(target.panel);
        break;
      case 'route':
        if (target.highlight)
          requestHighlight(target.highlight);
        startPromise(router.push(target.to));
        break;
      case 'run':
        target.run();
        break;
    }
  }

  return { openTarget };
}
