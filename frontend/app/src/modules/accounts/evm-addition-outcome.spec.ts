import { describe, expect, it } from 'vitest';
import { evmAdditionOutcome, EvmSkipReason } from '@/modules/accounts/evm-addition-outcome';

const ADDRESS = '0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1';

describe('evmAdditionOutcome', () => {
  it('should call an address added when it landed on any chain, keeping every other chain as detail', () => {
    expect(evmAdditionOutcome({
      added: { [ADDRESS]: ['eth'] },
      existed: { [ADDRESS]: ['base'] },
      failed: { [ADDRESS]: ['scroll'] },
      noActivity: { [ADDRESS]: ['gnosis', 'optimism'] },
    })).toStrictEqual({
      detail: { added: ['eth'], everyChain: false, existed: ['base'], failed: ['scroll'], noActivity: ['gnosis', 'optimism'] },
      type: 'added',
    });
  });

  it('should read the backend\'s all as every chain rather than as a chain named all', () => {
    const outcome = evmAdditionOutcome({ added: { [ADDRESS]: ['all'] } });

    expect(outcome).toStrictEqual({
      detail: { added: [], everyChain: true, existed: [], failed: [], noActivity: [] },
      type: 'added',
    });
  });

  it('should skip an address active on no chain, since the backend then tracks it nowhere', () => {
    expect(evmAdditionOutcome({ existed: { [ADDRESS]: ['eth'] }, noActivity: { [ADDRESS]: ['base'] } }))
      .toStrictEqual({ reason: EvmSkipReason.NO_ACTIVITY, type: 'skipped' });
  });

  it('should skip an address already tracked everywhere as tracked, not as inactive', () => {
    expect(evmAdditionOutcome({ existed: { [ADDRESS]: ['all'] } }))
      .toStrictEqual({ reason: EvmSkipReason.EXISTED, type: 'skipped' });
  });

  it('should fail an address that could be tracked on none of the chains it is active on', () => {
    expect(evmAdditionOutcome({ added: {}, failed: { [ADDRESS]: ['eth', 'base'] } }))
      .toStrictEqual({ chains: ['eth', 'base'], type: 'failed' });
  });
});
