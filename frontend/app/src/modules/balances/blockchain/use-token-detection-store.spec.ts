import type { EvmTokensRecord } from '@/modules/balances/types/balances';
import { beforeEach, describe, expect, it } from 'vitest';
import { useTokenDetectionStore } from './use-token-detection-store';

describe('useTokenDetectionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should initialize with empty state', () => {
    const store = useTokenDetectionStore();
    expect(get(store.tokensState)).toEqual({});
    expect(get(store.massDetecting)).toBeUndefined();
  });

  it('should set token state for a chain', () => {
    const store = useTokenDetectionStore();
    const data: EvmTokensRecord = {
      '0xaddr1': { lastUpdateTimestamp: 1000, tokens: ['DAI'] },
    };

    store.setState('eth', data);

    expect(get(store.tokensState).eth).toEqual(data);
  });

  it('should merge token state when setting for an existing chain', () => {
    const store = useTokenDetectionStore();

    store.setState('eth', {
      '0xaddr1': { lastUpdateTimestamp: 1000, tokens: ['DAI'] },
    });
    store.setState('eth', {
      '0xaddr2': { lastUpdateTimestamp: 2000, tokens: ['USDC'] },
    });

    const state = get(store.tokensState).eth;
    expect(state['0xaddr1']).toBeDefined();
    expect(state['0xaddr2']).toBeDefined();
  });

  it('should overwrite existing address data on re-set', () => {
    const store = useTokenDetectionStore();

    store.setState('eth', {
      '0xaddr1': { lastUpdateTimestamp: 1000, tokens: ['DAI'] },
    });
    store.setState('eth', {
      '0xaddr1': { lastUpdateTimestamp: 2000, tokens: ['DAI', 'USDC'] },
    });

    const info = get(store.tokensState).eth['0xaddr1'];
    expect(info.lastUpdateTimestamp).toBe(2000);
    expect(info.tokens).toEqual(['DAI', 'USDC']);
  });

  it('should keep state for different chains independent', () => {
    const store = useTokenDetectionStore();

    store.setState('eth', {
      '0xaddr1': { lastUpdateTimestamp: 1000, tokens: ['DAI'] },
    });
    store.setState('optimism', {
      '0xaddr2': { lastUpdateTimestamp: 2000, tokens: ['USDC'] },
    });

    expect(get(store.tokensState).eth['0xaddr1']).toBeDefined();
    expect(get(store.tokensState).optimism['0xaddr2']).toBeDefined();
    expect(get(store.tokensState).eth['0xaddr2']).toBeUndefined();
  });
});
