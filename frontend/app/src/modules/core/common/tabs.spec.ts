import { describe, expect, it } from 'vitest';
import { tabKey } from '@/modules/core/common/tabs';

describe('tabKey', () => {
  // The e2e suite writes these keys as literals, so the shape is a contract.
  it('should drop the leading slash and join segments with a dash', () => {
    expect(tabKey('/settings/rpc')).toBe('settings-rpc');
    expect(tabKey('/asset-manager/more/cex-mapping')).toBe('asset-manager-more-cex-mapping');
  });

  it('should lower-case the path', () => {
    expect(tabKey('/Settings/RPC')).toBe('settings-rpc');
  });

  it('should never emit a BEM separator', () => {
    expect(tabKey('/settings/general')).not.toContain('__');
  });
});
