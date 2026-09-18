import { describe, expect, it, vi } from 'vitest';
import { useTrackedAccountsRow } from '@/modules/accounts/use-tracked-accounts-row';
import { ActionUrgency } from '@/modules/core/action-center/types';

const tracksNothing = ref<boolean>(true);
const loading = ref<boolean>(false);

vi.mock('@/modules/accounts/use-tracked-entities', () => ({
  useTrackedEntities: (): object => ({ loading, tracksNothing }),
}));

describe('modules/accounts/use-tracked-accounts-row', () => {
  it('should raise a decision row pointing at the accounts page when nothing is tracked', () => {
    set(tracksNothing, true);
    set(loading, false);
    const { raised, row } = useTrackedAccountsRow();

    expect(get(raised)).toBe(true);
    expect(get(row)).toMatchObject({
      count: 1,
      id: 'no-tracked-accounts',
      target: { kind: 'route', to: { name: '/accounts/' } },
      urgency: ActionUrgency.DECISION,
    });
  });

  it('should offer every kind of source as a choice, each opening the dialog that adds one', () => {
    const { row } = useTrackedAccountsRow();
    const { choices } = get(row);

    expect(choices.map(choice => choice.id)).toEqual([
      'add-evm',
      'add-bitcoin',
      'add-solana',
      'add-substrate',
      'add-exchange',
      'add-bank',
      'add-manual',
    ]);
    expect(choices.find(choice => choice.id === 'add-bank')?.target).toEqual({
      kind: 'route',
      to: { name: '/api-keys/banks/', query: { add: 'true' } },
    });
  });

  it('should not raise it while the accounts are still being read, since an empty store is not an answer yet', () => {
    set(tracksNothing, true);
    set(loading, true);
    const { raised, row } = useTrackedAccountsRow();

    expect(get(raised)).toBe(false);
    expect(get(row).loading).toBe(true);
  });

  it('should clear it once anything is tracked', () => {
    set(tracksNothing, false);
    set(loading, false);
    const { raised, row } = useTrackedAccountsRow();

    expect(get(raised)).toBe(false);
    expect(get(row).count).toBe(0);
  });
});
