import { createCustomPinia } from '@test/utils/create-pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useConfirm } from '@/modules/core/common/use-confirm';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';

describe('useConfirm', () => {
  let store: ReturnType<typeof useConfirmStore>;
  let ask: ReturnType<typeof useConfirm>['ask'];

  beforeEach(() => {
    setActivePinia(createCustomPinia());
    store = useConfirmStore();
    ({ ask } = useConfirm());
  });

  const title = 'confirmation title';
  const message = 'confirmation message';

  it('should show the question in the store while it is asked', async () => {
    const answer = ask({ message, title });

    expect(get(storeToRefs(store).visible)).toBe(true);
    expect(get(storeToRefs(store).confirmation)).toMatchObject({ message, title });
    store.dismiss();
    await answer;
  });

  it('should settle with confirm when confirmed', async () => {
    const answer = ask({ message, title });
    store.confirm();
    await expect(answer).resolves.toBe('confirm');
  });

  it('should settle with dismiss when backed out', async () => {
    const answer = ask({ message, title });
    store.dismiss();
    await expect(answer).resolves.toBe('dismiss');
  });

  it('should settle with alternative when the alternative is picked, never on backing out', async () => {
    const backedOut = ask({ alternativeAction: 'Exclude', message, title });
    store.dismiss();
    await expect(backedOut).resolves.toBe('dismiss');

    const picked = ask({ alternativeAction: 'Exclude', message, title });
    store.alternative();
    await expect(picked).resolves.toBe('alternative');
  });

  it('should treat escaping an acknowledgement as acknowledging it', async () => {
    const answer = ask({ message, singleAction: true, title });
    store.dismiss();
    await expect(answer).resolves.toBe('confirm');
  });

  it('should settle a question still on screen as dismissed when another is asked, and show the new one', async () => {
    const first = ask({ message: 'first', title });
    const second = ask({ message: 'second', title });

    await expect(first).resolves.toBe('dismiss');
    expect(get(storeToRefs(store).confirmation).message).toBe('second');

    store.confirm();
    await expect(second).resolves.toBe('confirm');
  });
});
