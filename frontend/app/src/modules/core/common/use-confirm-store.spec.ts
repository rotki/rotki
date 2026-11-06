import { createCustomPinia } from '@test/utils/create-pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type ConfirmChoice, useConfirmStore } from '@/modules/core/common/use-confirm-store';

describe('useConfirmStore', () => {
  let store: ReturnType<typeof useConfirmStore>;
  let onAnswer: ReturnType<typeof vi.fn<(choice: ConfirmChoice) => void>>;

  beforeEach(() => {
    setActivePinia(createCustomPinia());
    store = useConfirmStore();
    onAnswer = vi.fn<(choice: ConfirmChoice) => void>();
    vi.useFakeTimers();
  });

  const title = 'confirmation title';
  const message = 'confirmation message';

  it('should show the question while it is open, and clear it a while after it is answered', () => {
    const { visible, confirmation } = storeToRefs(store);
    expect(get(visible)).toBe(false);

    store.open({ message, title }, onAnswer);

    expect(get(visible)).toBe(true);
    expect(get(confirmation)).toMatchObject({ message, title });

    store.confirm();
    expect(get(visible)).toBe(false);

    vi.runAllTimers();
    expect(get(confirmation)).toMatchObject({ message: '', title: '' });
  });

  it('should answer confirm when confirmed', () => {
    store.open({ message, title }, onAnswer);
    store.confirm();
    expect(onAnswer).toHaveBeenCalledExactlyOnceWith('confirm');
  });

  it('should answer dismiss when backed out', () => {
    store.open({ message, title }, onAnswer);
    store.dismiss();
    expect(onAnswer).toHaveBeenCalledExactlyOnceWith('dismiss');
  });

  it('should answer alternative when the alternative is picked', () => {
    store.open({ alternativeAction: 'Exclude', message, title }, onAnswer);
    store.alternative();
    expect(onAnswer).toHaveBeenCalledExactlyOnceWith('alternative');
  });

  it('should answer an escaped acknowledgement as confirmed', () => {
    store.open({ message, singleAction: true, title }, onAnswer);
    store.dismiss();
    expect(onAnswer).toHaveBeenCalledExactlyOnceWith('confirm');
  });

  it('should answer a question once, ignoring a second answer', () => {
    store.open({ message, title }, onAnswer);
    store.confirm();
    store.dismiss();
    expect(onAnswer).toHaveBeenCalledExactlyOnceWith('confirm');
  });

  it('should answer a question still on screen as dismissed when another opens, and show the new one', () => {
    const second = vi.fn<(choice: ConfirmChoice) => void>();
    store.open({ message: 'first', title }, onAnswer);
    store.open({ message: 'second', title }, second);

    expect(onAnswer).toHaveBeenCalledExactlyOnceWith('dismiss');
    expect(second).not.toHaveBeenCalled();
    expect(get(storeToRefs(store).confirmation).message).toBe('second');

    store.confirm();
    expect(second).toHaveBeenCalledExactlyOnceWith('confirm');
  });
});
