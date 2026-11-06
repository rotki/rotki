import { type ConfirmationMessage, type ConfirmChoice, useConfirmStore } from '@/modules/core/common/use-confirm-store';

interface UseConfirmReturn {
  /**
   * Opens the app-wide confirmation and settles with how it was answered.
   *
   * @remarks
   * Settles on every way out, so an awaiting caller cannot hang on a cancel. A question still on
   * screen when another is asked settles as dismissed. Escape on a `singleAction` acknowledgement
   * settles as confirmed.
   */
  ask: (message: ConfirmationMessage) => Promise<ConfirmChoice>;
}

/**
 * Asks through the app-wide confirmation dialog, for the few questions with nowhere better to be
 * asked (see `useConfirmStore`).
 */
export function useConfirm(): UseConfirmReturn {
  const { open } = useConfirmStore();

  async function ask(message: ConfirmationMessage): Promise<ConfirmChoice> {
    return new Promise<ConfirmChoice>((resolve) => {
      open(message, resolve);
    });
  }

  return { ask };
}
