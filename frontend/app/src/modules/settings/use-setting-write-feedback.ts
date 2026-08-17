import type { Ref } from 'vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';

/** The parts of a {@link useSettingModel} return this needs; extra fields are ignored. */
interface SettingWriteState<T> {
  readonly model: Ref<T>;
  readonly error: Readonly<Ref<string>>;
  readonly success: Readonly<Ref<boolean>>;
}

interface UseSettingWriteFeedbackReturn {
  readonly error: Readonly<Ref<string>>;
  readonly success: Readonly<Ref<string>>;
}

/**
 * Turns a setting model's `{ success, error }` flags into the transient message pair a form row
 * renders, and clears both as soon as the draft changes again.
 *
 * `successMessage` is read at fire time rather than passed as a string, so it can name whatever the
 * write was about (for example the chain whose order was just saved).
 */
export function useSettingWriteFeedback<T>(
  state: SettingWriteState<T>,
  successMessage: () => string,
): UseSettingWriteFeedbackReturn {
  const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

  watch(state.model, () => {
    clearAll();
  });

  watch(state.success, (saved) => {
    if (saved)
      setSuccess(successMessage(), true);
  });

  watch(state.error, (message) => {
    if (message)
      setError(message, true);
  });

  return { error, success };
}
