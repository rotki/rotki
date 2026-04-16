import { createCustomPinia } from '@test/utils/create-pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';

describe('useConfirmStore', () => {
  let store: ReturnType<typeof useConfirmStore>;

  beforeEach(() => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    store = useConfirmStore();
    vi.useFakeTimers();
  });

  const title = 'confirmation title';
  const message = 'confirmation message';

  it('should show confirmation message', () => {
    const confirmationMessage = {
      title,
      message,
    };
    const { show } = store;
    const { visible, confirmation } = storeToRefs(store);

    expect(get(visible)).toBe(false);
    expect(get(confirmation).title).toBe('');
    expect(get(confirmation).message).toBe('');

    show(confirmationMessage, () => {});

    expect(get(visible)).toBe(true);
    expect(get(confirmation).title).toBe(title);
    expect(get(confirmation).message).toBe(message);
  });

  it('should call onConfirm callback', async () => {
    const confirmationMessage = {
      title,
      message,
    };
    const { show, confirm } = store;
    const { visible, confirmation } = storeToRefs(store);

    expect(get(visible)).toBe(false);

    const onConfirm = vi.fn();
    show(confirmationMessage, onConfirm);

    expect(get(visible)).toBe(true);

    // should call confirm callback
    await confirm();

    expect(get(visible)).toBe(false);
    expect(onConfirm).toBeCalledTimes(1);

    vi.runAllTimers();

    expect(get(confirmation).title).toBe('');
    expect(get(confirmation).message).toBe('');

    // should not call confirm again, since the method should be cleared.
    await confirm();
    expect(onConfirm).toBeCalledTimes(1);
  });

  it('should call onDismiss callback', async () => {
    const confirmationMessage = {
      title,
      message,
    };
    const { show, dismiss } = store;
    const { visible, confirmation } = storeToRefs(store);

    expect(get(visible)).toBe(false);

    const onDismiss = vi.fn();
    show(confirmationMessage, () => {}, onDismiss);

    expect(get(visible)).toBe(true);

    // should call dismiss callback
    await dismiss();

    expect(get(visible)).toBe(false);
    expect(onDismiss).toBeCalledTimes(1);

    vi.runAllTimers();

    expect(get(confirmation).title).toBe('');
    expect(get(confirmation).message).toBe('');

    // should not call dismiss again, since the method should be cleared.
    await dismiss();
    expect(onDismiss).toBeCalledTimes(1);
  });
});
