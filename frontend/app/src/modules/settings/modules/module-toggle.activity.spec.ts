import { describe, expect, it } from 'vitest';
import { Module } from '@/modules/core/common/modules';
import { moduleToggleActivity } from '@/modules/settings/modules/module-toggle.activity';

describe('module toggle activity ids', () => {
  it('should key a toggle by module and direction', () => {
    expect(moduleToggleActivity.id({ enabled: true, module: Module.NFTS })).toBe('module-toggle:nfts:enabled');
    expect(moduleToggleActivity.id({ enabled: false, module: Module.NFTS })).toBe('module-toggle:nfts:disabled');
  });

  it('should give the parts the NFT balances go stale on', () => {
    expect(moduleToggleActivity.partsOf({ enabled: true, module: Module.NFTS })).toStrictEqual(['nfts', 'enabled']);
  });
});
