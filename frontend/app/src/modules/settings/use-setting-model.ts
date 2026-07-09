import type { Ref } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import { startPromise } from '@shared/utils';
import { isEqual } from 'es-toolkit';
import { useSettingsWriter, type WritableSettingKey } from '@/modules/settings/settings-writer';
import { type SettingValue, useSetting } from '@/modules/settings/use-setting';

interface UseSettingModelOptions {
  /** Debounce persistence by this many ms (e.g. text inputs). Omit or 0 to persist immediately. */
  readonly debounce?: number;
}

interface UseSettingModelReturn<K extends WritableSettingKey> {
  /** Local writable draft. Binds to an input; assigning it persists through the writer. */
  readonly model: Ref<SettingValue<K>>;
  readonly pending: Readonly<Ref<boolean>>;
  readonly error: Readonly<Ref<string>>;
  readonly success: Readonly<Ref<boolean>>;
}

/**
 * Form-facing write model for a single setting. Returns a local draft ref that the input binds to;
 * changing it persists through `useSettingsWriter` (debounced when configured) and reports
 * `{ pending, error, success }`. The draft stays in sync when the persisted value changes elsewhere.
 * Keeps the reactive setter side-effect-free: the input only mutates the local draft, and all network
 * I/O runs in the watcher via the writer.
 */
export function useSettingModel<K extends WritableSettingKey>(
  key: K,
  options: UseSettingModelOptions = {},
): UseSettingModelReturn<K> {
  const { debounce = 0 } = options;
  const { write } = useSettingsWriter();
  const source = useSetting(key);

  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- shallowRef's value type mirrors the source value type; the draft is replaced wholesale, never deep-mutated
  const model = shallowRef(get(source)) as Ref<SettingValue<K>>;
  const pending = shallowRef<boolean>(false);
  const error = shallowRef<string>('');
  const success = shallowRef<boolean>(false);

  // Reflect persisted/external changes into the local draft (skip if already equal to avoid a write echo).
  watch(source, (value) => {
    if (!isEqual(value, get(model)))
      set(model, value);
  });

  const persist = async (): Promise<void> => {
    // Read the live draft at fire time. A debounced fire can be stale: if the draft was changed again
    // during the window (in particular reverted back to the persisted value), there is nothing to write.
    const value = get(model);
    if (isEqual(value, get(source)))
      return;
    set(pending, true);
    set(error, '');
    set(success, false);
    const result: ActionStatus = await write(key, value);
    set(pending, false);
    if (result.success)
      set(success, true);
    else
      set(error, result.message ?? '');
  };

  const schedule = debounce > 0 ? useDebounceFn(persist, debounce) : persist;

  watch(model, (value) => {
    if (isEqual(value, get(source)))
      return;
    startPromise(schedule());
  });

  return {
    error: readonly(error),
    model,
    pending: readonly(pending),
    success: readonly(success),
  };
}
