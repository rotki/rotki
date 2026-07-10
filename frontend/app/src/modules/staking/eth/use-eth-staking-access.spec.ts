import type { Ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PremiumFeature } from '@/modules/premium/use-feature-access';
import { Module } from '@/modules/session/use-module-enabled';
import { useEthStakingAccess } from '@/modules/staking/eth/use-eth-staking-access';

const mockEnabled = ref<boolean>(true);
const mockAllowed = ref<boolean>(true);
const mockUseModuleEnabled = vi.fn((_module: Module) => ({ enabled: mockEnabled }));
const mockUseFeatureAccess = vi.fn((_feature: PremiumFeature) => ({ allowed: mockAllowed }));

vi.mock('@/modules/session/use-module-enabled', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/session/use-module-enabled')>(),
  useModuleEnabled: (module: Module): { enabled: Ref<boolean> } => mockUseModuleEnabled(module),
}));

vi.mock('@/modules/premium/use-feature-access', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/premium/use-feature-access')>(),
  useFeatureAccess: (feature: PremiumFeature): { allowed: Ref<boolean> } => mockUseFeatureAccess(feature),
}));

describe('useEthStakingAccess', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(mockEnabled, true);
    set(mockAllowed, true);
  });

  it('should expose the eth2 module', () => {
    const { module } = useEthStakingAccess();
    expect(module).toBe(Module.ETH2);
  });

  it('should check module enablement for eth2', () => {
    useEthStakingAccess();
    expect(mockUseModuleEnabled).toHaveBeenCalledWith(Module.ETH2);
  });

  it('should check feature access for the eth staking view', () => {
    useEthStakingAccess();
    expect(mockUseFeatureAccess).toHaveBeenCalledWith(PremiumFeature.ETH_STAKING_VIEW);
  });

  it('should reflect the module enabled state', () => {
    set(mockEnabled, false);
    const { enabled } = useEthStakingAccess();
    expect(get(enabled)).toBe(false);
  });

  it('should reflect the feature allowed state', () => {
    set(mockAllowed, false);
    const { allowed } = useEthStakingAccess();
    expect(get(allowed)).toBe(false);
  });
});
