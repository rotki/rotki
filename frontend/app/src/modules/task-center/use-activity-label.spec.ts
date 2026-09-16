import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { msg } from '@/message-key';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { type Activity, ActivityKind, ActivitySourceType, ActivityStatus, type ActivityText, makeActivityId } from './core/types';
import { useActivityLabel } from './use-activity-label';

const ADDRESS = '0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1';

function activity(subtitle: ActivityText | undefined): Activity {
  return {
    cancellable: false,
    id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'eth'),
    kind: ActivityKind.BLOCKCHAIN_BALANCES,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status: ActivityStatus.RUNNING,
    subtitle,
    title: 'Blockchain balances',
  };
}

describe('useActivityLabel', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should call a top-level activity by its title', () => {
    const chain = activity({ key: msg.$t('task_center.activity.blockchain_balances.chain'), params: { chain: 'Ethereum' } });

    expect(useActivityLabel().labelOf(chain, false)).toBe('Blockchain balances');
  });

  it('should call a nested activity by what it acts on, dropping the verb its siblings share', () => {
    const chain = activity({ key: msg.$t('task_center.activity.blockchain_balances.chain'), params: { chain: 'Ethereum' } });

    expect(useActivityLabel().labelOf(chain, true)).toBe('Ethereum');
  });

  it('should prefer the address to the chain for an account nested under a chain', () => {
    const account = activity({ key: msg.$t('task_center.activity.tx_sync.address'), params: { address: ADDRESS, chain: 'Ethereum' } });

    expect(useActivityLabel().labelOf(account, true)).toBe(ADDRESS);
  });

  it('should scramble the address it names while privacy mode is on', () => {
    useSettingsRepo().updateFrontend({ scrambleData: true, scrambleMultiplier: 7 });
    const account = activity({ key: msg.$t('task_center.activity.tx_sync.address'), params: { address: ADDRESS, chain: 'Ethereum' } });

    expect(useActivityLabel().labelOf(account, true)).not.toBe(ADDRESS);
  });

  it('should keep the account beside the exchange, since two accounts on one exchange are otherwise the same', () => {
    const exchange = activity({ key: msg.$t('task_center.activity.history_events.exchange'), params: { account: 'main', exchange: 'Kraken' } });

    expect(useActivityLabel().labelOf(exchange, true)).toBe('Kraken (main)');
  });

  it('should show the whole subtitle when it names nothing to act on', () => {
    const detect = activity({ key: msg.$t('task_center.activity.accounts.detect') });

    expect(useActivityLabel().labelOf(detect, true)).toBe('task_center.activity.accounts.detect');
  });

  it('should show a plain-string subtitle as it is, and fall back to the title with none', () => {
    const { labelOf } = useActivityLabel();

    expect(labelOf(activity('Ethereum'), true)).toBe('Ethereum');
    expect(labelOf(activity(undefined), true)).toBe('Blockchain balances');
  });
});
