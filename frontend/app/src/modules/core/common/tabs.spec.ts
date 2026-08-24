import { describe, expect, it } from 'vitest';
import { tabTestId } from '@/modules/core/common/tabs';

describe('tabTestId', () => {
  // The e2e suite writes these ids as literals, so the shape is a contract.
  it('should drop the leading slash and join segments with a dash', () => {
    expect(tabTestId('/settings/rpc')).toBe('settings-rpc');
    expect(tabTestId('/asset-manager/more/cex-mapping')).toBe('asset-manager-more-cex-mapping');
  });

  it('should lower-case the path', () => {
    expect(tabTestId('/Settings/RPC')).toBe('settings-rpc');
  });

  it('should never emit a BEM separator', () => {
    expect(tabTestId('/settings/general')).not.toContain('__');
  });
});
