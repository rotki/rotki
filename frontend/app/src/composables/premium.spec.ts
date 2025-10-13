import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { usePremiumStore } from '@/store/session/premium';
import { PremiumFeature } from '@/types/session';
import { usePremiumHelper } from './premium';

describe('composables/premium', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  describe('usePremiumHelper', () => {
    describe('isFeatureAllowed', () => {
      it('should return false when user is not premium', () => {
        const { isFeatureAllowed } = usePremiumHelper();

        const ethStakingAllowed = isFeatureAllowed(PremiumFeature.ETH_STAKING_VIEW);
        const graphsAllowed = isFeatureAllowed(PremiumFeature.GRAPHS_VIEW);
        const eventAnalysisAllowed = isFeatureAllowed(PremiumFeature.EVENT_ANALYSIS_VIEW);

        expect(get(ethStakingAllowed)).toBe(false);
        expect(get(graphsAllowed)).toBe(false);
        expect(get(eventAnalysisAllowed)).toBe(false);
      });

      it('should return false when user is premium but capabilities are not loaded', () => {
        const store = usePremiumStore();
        const { premium } = storeToRefs(store);
        set(premium, true);

        const { isFeatureAllowed } = usePremiumHelper();

        const ethStakingAllowed = isFeatureAllowed(PremiumFeature.ETH_STAKING_VIEW);
        const graphsAllowed = isFeatureAllowed(PremiumFeature.GRAPHS_VIEW);
        const eventAnalysisAllowed = isFeatureAllowed(PremiumFeature.EVENT_ANALYSIS_VIEW);

        expect(get(ethStakingAllowed)).toBe(false);
        expect(get(graphsAllowed)).toBe(false);
        expect(get(eventAnalysisAllowed)).toBe(false);
      });

      it('should return correct value when user is premium and capabilities are loaded', () => {
        const store = usePremiumStore();
        const { capabilities, premium } = storeToRefs(store);
        set(premium, true);
        set(capabilities, {
          ethStakingView: true,
          eventAnalysisView: true,
          graphsView: false,
        });

        const { isFeatureAllowed } = usePremiumHelper();

        const ethStakingAllowed = isFeatureAllowed(PremiumFeature.ETH_STAKING_VIEW);
        const graphsAllowed = isFeatureAllowed(PremiumFeature.GRAPHS_VIEW);
        const eventAnalysisAllowed = isFeatureAllowed(PremiumFeature.EVENT_ANALYSIS_VIEW);

        expect(get(ethStakingAllowed)).toBe(true);
        expect(get(graphsAllowed)).toBe(false);
        expect(get(eventAnalysisAllowed)).toBe(true);
      });

      it('should return false for missing capability in response (schema defaults)', () => {
        const store = usePremiumStore();
        const { capabilities, premium } = storeToRefs(store);
        set(premium, true);
        // Simulate a response missing some capabilities (zod will use defaults)
        set(capabilities, {
          ethStakingView: true,
          eventAnalysisView: false,
          graphsView: false,
        });

        const { isFeatureAllowed } = usePremiumHelper();

        const ethStakingAllowed = isFeatureAllowed(PremiumFeature.ETH_STAKING_VIEW);
        const graphsAllowed = isFeatureAllowed(PremiumFeature.GRAPHS_VIEW);
        const eventAnalysisAllowed = isFeatureAllowed(PremiumFeature.EVENT_ANALYSIS_VIEW);

        expect(get(ethStakingAllowed)).toBe(true);
        expect(get(graphsAllowed)).toBe(false);
        expect(get(eventAnalysisAllowed)).toBe(false);
      });

      it('should reactively update when capabilities change', async () => {
        const store = usePremiumStore();
        const { capabilities, premium } = storeToRefs(store);
        set(premium, true);
        set(capabilities, {
          ethStakingView: false,
          eventAnalysisView: false,
          graphsView: false,
        });

        const { isFeatureAllowed } = usePremiumHelper();
        const ethStakingAllowed = isFeatureAllowed(PremiumFeature.ETH_STAKING_VIEW);

        expect(get(ethStakingAllowed)).toBe(false);

        // Update capabilities
        set(capabilities, {
          ethStakingView: true,
          eventAnalysisView: false,
          graphsView: false,
        });

        await nextTick();
        expect(get(ethStakingAllowed)).toBe(true);
      });

      it('should reactively update when premium status changes', async () => {
        const store = usePremiumStore();
        const { capabilities, premium } = storeToRefs(store);
        set(premium, true);
        set(capabilities, {
          ethStakingView: true,
          eventAnalysisView: true,
          graphsView: true,
        });

        const { isFeatureAllowed } = usePremiumHelper();
        const ethStakingAllowed = isFeatureAllowed(PremiumFeature.ETH_STAKING_VIEW);

        expect(get(ethStakingAllowed)).toBe(true);

        // User loses premium status
        set(premium, false);

        await nextTick();
        expect(get(ethStakingAllowed)).toBe(false);
      });
    });
  });
});
