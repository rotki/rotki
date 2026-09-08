import type { SupportedAsset } from '@rotki/common';
import type { AssetUpdateConflictResult } from '@/modules/assets/types';
import { describe, expect, it } from 'vitest';
import {
  getConflictFields,
  isDiff,
  useAssetConflictResolution,
} from '@/modules/shell/app/use-asset-conflict-resolution';

/**
 * A real asset, not `createMock`: `getConflictFields` enumerates the keys, and a proxy answers
 * every property, so a mock reports its own internals as fields of the asset.
 */
function asset(overrides: Partial<SupportedAsset>): SupportedAsset {
  return { identifier: 'eth', isRebasing: false, ...overrides };
}

function conflict(identifier: string, local: Partial<SupportedAsset> = {}, remote: Partial<SupportedAsset> = {}): AssetUpdateConflictResult {
  return {
    identifier,
    local: asset({ identifier, ...local }),
    remote: asset({ identifier, ...remote }),
  };
}

describe('useAssetConflictResolution', () => {
  describe('resolving every conflict at once', () => {
    it('should give every conflict the chosen strategy', () => {
      const { modelResolution, setResolution } = useAssetConflictResolution([conflict('eth'), conflict('btc')]);

      setResolution('remote');

      expect(get(modelResolution)).toEqual({ btc: 'remote', eth: 'remote' });
    });

    it('should replace an earlier choice rather than merge into it', () => {
      const { modelResolution, setResolution } = useAssetConflictResolution([conflict('eth')]);

      setResolution('remote');
      setResolution('local');

      expect(get(modelResolution)).toEqual({ eth: 'local' });
    });

    it('should press the button for the strategy applied to all', () => {
      const { activeStrategyForAll, setResolution } = useAssetConflictResolution([conflict('eth')]);

      setResolution('local');

      expect(get(activeStrategyForAll)).toEqual({ local: true, remote: false });
    });

    it('should press neither button before anything is chosen', () => {
      const { activeStrategyForAll } = useAssetConflictResolution([conflict('eth')]);

      expect(get(activeStrategyForAll)).toEqual({ local: false, remote: false });
    });

    it('should press neither button when a row was changed by hand', () => {
      const { activeStrategyForAll, modelResolution, onStrategyChange, setResolution } = useAssetConflictResolution([
        conflict('eth'),
        conflict('btc'),
      ]);

      setResolution('remote');
      set(modelResolution, { ...get(modelResolution), btc: 'local' });
      onStrategyChange('local');

      expect(get(activeStrategyForAll)).toEqual({ local: false, remote: false });
    });

    it('should press the button again once every row agrees', () => {
      const { activeStrategyForAll, modelResolution, onStrategyChange } = useAssetConflictResolution([
        conflict('eth'),
        conflict('btc'),
      ]);

      set(modelResolution, { btc: 'local', eth: 'local' });
      onStrategyChange('local');

      expect(get(activeStrategyForAll)).toEqual({ local: true, remote: false });
    });
  });

  describe('whether the dialog can be confirmed', () => {
    it('should not be valid while a conflict is unresolved', () => {
      const { modelResolution, valid } = useAssetConflictResolution([conflict('eth'), conflict('btc')]);

      set(modelResolution, { eth: 'local' });

      expect(get(valid)).toBe(false);
    });

    it('should be valid once every conflict has a strategy', () => {
      const { setResolution, valid } = useAssetConflictResolution([conflict('eth'), conflict('btc')]);

      setResolution('local');

      expect(get(valid)).toBe(true);
    });

    /**
     * The counts can match while the identifiers do not, which would send a resolution for an
     * asset the update never reported and leave a real conflict unanswered.
     */
    it('should not be valid when a resolution names an asset that is not in conflict', () => {
      const { modelResolution, valid } = useAssetConflictResolution([conflict('eth'), conflict('btc')]);

      set(modelResolution, { btc: 'local', doge: 'local' });

      expect(get(valid)).toBe(false);
    });

    it('should be valid with one resolution when the same asset conflicts twice', () => {
      const { setResolution, valid } = useAssetConflictResolution([conflict('eth'), conflict('eth')]);

      setResolution('local');

      expect(get(valid)).toBe(true);
    });
  });

  describe('what is left to do', () => {
    it('should count every distinct asset before anything is chosen', () => {
      const { remaining } = useAssetConflictResolution([conflict('eth'), conflict('btc')]);

      expect(get(remaining)).toBe(2);
    });

    it('should count a repeated asset once', () => {
      const { remaining } = useAssetConflictResolution([conflict('eth'), conflict('eth'), conflict('btc')]);

      expect(get(remaining)).toBe(2);
    });

    it('should reach zero once every conflict is resolved', () => {
      const { remaining, setResolution } = useAssetConflictResolution([conflict('eth'), conflict('btc')]);

      setResolution('remote');

      expect(get(remaining)).toBe(0);
    });
  });

  describe('the duplicate warning', () => {
    it('should not warn when every identifier is distinct', () => {
      const { duplicateIdentifiers, warnDuplicate } = useAssetConflictResolution([conflict('eth'), conflict('btc')]);

      expect(get(warnDuplicate)).toBe(false);
      expect(get(duplicateIdentifiers)).toEqual([]);
    });

    it('should name the identifier that arrived more than once', () => {
      const { duplicateIdentifiers, warnDuplicate } = useAssetConflictResolution([
        conflict('eth'),
        conflict('btc'),
        conflict('eth'),
      ]);

      expect(get(warnDuplicate)).toBe(true);
      expect(get(duplicateIdentifiers)).toEqual(['eth']);
    });
  });

  describe('the dialog state', () => {
    it('should start on the bulk choices and stay dismissable', () => {
      const { hasResolution, manualResolution } = useAssetConflictResolution([conflict('eth')]);

      expect(get(manualResolution)).toBe(false);
      expect(get(hasResolution)).toBe(false);
    });

    it('should stop being dismissable once a strategy is chosen', () => {
      const { hasResolution, setResolution } = useAssetConflictResolution([conflict('eth')]);

      setResolution('remote');

      expect(get(hasResolution)).toBe(true);
    });

    it('should switch to resolving by hand', () => {
      const { enableManualResolution, manualResolution } = useAssetConflictResolution([conflict('eth')]);

      enableManualResolution();

      expect(get(manualResolution)).toBe(true);
    });
  });

  describe('reacting to the conflicts it is given', () => {
    it('should follow a changing list', () => {
      const conflicts = ref<AssetUpdateConflictResult[]>([conflict('eth')]);
      const { remaining } = useAssetConflictResolution(conflicts);

      set(conflicts, [conflict('eth'), conflict('btc')]);

      expect(get(remaining)).toBe(2);
    });

    it('should press neither button when there is nothing to resolve', () => {
      const { activeStrategyForAll } = useAssetConflictResolution([]);

      expect(get(activeStrategyForAll)).toEqual({ local: false, remote: false });
    });
  });
});

describe('getConflictFields', () => {
  it('should list a field either side has a value for', () => {
    const fields = getConflictFields(conflict('eth', { name: 'Ether', symbol: null }, { name: null, symbol: 'ETH' }));

    expect(fields).toContain('name');
    expect(fields).toContain('symbol');
  });

  it('should list a field once when both sides have it', () => {
    const fields = getConflictFields(conflict('eth', { name: 'Ether' }, { name: 'Ethereum' }));

    expect(fields.filter(field => field === 'name')).toHaveLength(1);
  });

  it('should drop a field neither side has a value for', () => {
    const fields = getConflictFields(conflict('eth', { coingecko: null }, { coingecko: null }));

    expect(fields).not.toContain('coingecko');
  });
});

describe('isDiff', () => {
  it('should report a field the two sides disagree on', () => {
    expect(isDiff(conflict('eth', { name: 'Ether' }, { name: 'Ethereum' }), 'name')).toBe(true);
  });

  it('should report no difference when the values match', () => {
    expect(isDiff(conflict('eth', { name: 'Ether' }, { name: 'Ether' }), 'name')).toBe(false);
  });
});
