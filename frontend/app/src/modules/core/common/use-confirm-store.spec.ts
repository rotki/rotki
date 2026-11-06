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

  it('should keep the alternative apart from backing out, so dismissing never takes it', async () => {
    const { alternative, dismiss, show } = store;
    const onDismiss = vi.fn();
    const onAlternative = vi.fn();

    show({ alternativeAction: 'Exclude', message, title }, () => {}, onDismiss, onAlternative);
    await dismiss();

    expect(onDismiss).toHaveBeenCalledOnce();
    expect(onAlternative).not.toHaveBeenCalled();

    show({ alternativeAction: 'Exclude', message, title }, () => {}, onDismiss, onAlternative);
    await alternative();

    expect(onAlternative).toHaveBeenCalledOnce();
    expect(onDismiss).toHaveBeenCalledOnce();
    expect(get(storeToRefs(store).visible)).toBe(false);

    await alternative();
    expect(onAlternative).toHaveBeenCalledOnce();
  });

  it('should treat escaping an acknowledgement as acknowledging it', async () => {
    const { dismiss, show } = store;
    const onConfirm = vi.fn();
    const onDismiss = vi.fn();

    show({ message, singleAction: true, title }, onConfirm, onDismiss);
    await dismiss();

    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onDismiss).not.toHaveBeenCalled();
    expect(get(storeToRefs(store).visible)).toBe(false);
  });

  describe('ask', () => {
    it('should settle with confirm when confirmed', async () => {
      const answer = store.ask({ message, title });
      await store.confirm();
      await expect(answer).resolves.toBe('confirm');
    });

    it('should settle with dismiss when backed out', async () => {
      const answer = store.ask({ message, title });
      await store.dismiss();
      await expect(answer).resolves.toBe('dismiss');
    });

    it('should settle with alternative when the alternative is offered and picked', async () => {
      const answer = store.ask({ alternativeAction: 'Exclude', message, title });
      await store.alternative();
      await expect(answer).resolves.toBe('alternative');
    });
  });
});
