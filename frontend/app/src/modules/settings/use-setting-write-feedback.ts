import type { Ref } from 'vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';

/** The parts of a {@link useSettingModel} return this needs; extra fields are ignored. */
interface SettingWriteState<T> {
  readonly model: Ref<T>;
  readonly error: Readonly<Ref<string>>;
  readonly success: Readonly<Ref<boolean>>;
}

interface SettingWriteFeedbackOptions {
  /** Prefixes the writer's error message, read at fire time like `successMessage`. */
  errorPrefix?: () => string;
  /** Runs after the success message is shown, for a control that announces the save. */
  onSaved?: () => void;
}

interface UseSettingWriteFeedbackReturn {
  readonly error: Readonly<Ref<string>>;
  readonly success: Readonly<Ref<string>>;
  /** Clears both messages, for a control that resets them on input before the draft changes. */
  readonly clearAll: () => void;
}

/** A setting control's message prop: static text, or a callback given the value it describes. */
export type SettingMessage<T> = string | ((value: T) => string);

/** Resolves a {@link SettingMessage} against the value it describes. */
export function resolveSettingMessage<T>(message: SettingMessage<T>, value: T): string {
  return typeof message === 'function' ? message(value) : message;
}

/**
 * Turns a setting model's `{ success, error }` flags into the transient message pair a form row
 * renders, and clears both as soon as the draft changes again.
 *
 * `successMessage` is read at fire time rather than passed as a string, so it can name whatever the
 * write was about (for example the chain whose order was just saved).
 *
 * The clear runs synchronously with the draft change. A rejected write reverts the draft and sets
 * its error in the same tick, and a queued clear could otherwise run after the error was shown.
 */
export function useSettingWriteFeedback<T>(
  state: SettingWriteState<T>,
  successMessage: () => string,
  options: SettingWriteFeedbackOptions = {},
): UseSettingWriteFeedbackReturn {
  const { errorPrefix, onSaved } = options;
  const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

  watch(state.model, () => {
    clearAll();
  }, { flush: 'sync' });

  watch(state.success, (saved) => {
    if (!saved)
      return;

    setSuccess(successMessage(), true);
    onSaved?.();
  });

  watch(state.error, (message) => {
    if (!message)
      return;

    const prefix = errorPrefix?.();
    setError(prefix ? `${prefix}: ${message}` : message, true);
  });

  return { clearAll, error, success };
}
