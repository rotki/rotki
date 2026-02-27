import type { ActionResult } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessionAuthStore } from '@/store/session/auth';
import { usePremiumStore } from '@/store/session/premium';
import { type PremiumCapabilities, PremiumFeature, type PremiumFeatureCapability } from '@/types/session';
import { usePremiumHelper } from './premium';

const backendUrl = process.env.VITE_BACKEND_URL;

function cap(enabled: boolean, minimumTier = 'Free'): PremiumFeatureCapability {
  return { enabled, minimumTier };
}

function mockPremiumCapabilities<T = PremiumCapabilities>(capabilities: T, status: number = 200): ReturnType<typeof http.get> {
  return http.get(`${backendUrl}/api/1/premium/capabilities`, () =>
    HttpResponse.json<ActionResult<T>>({
      message: '',
      result: capabilities,
    }, { status }));
}

describe('composables/premium', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  describe('usePremiumHelper', () => {
    beforeEach(() => {
      const { logged } = storeToRefs(useSessionAuthStore());
      set(logged, true);
    });

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
          assetMovementMatching: cap(false),
          ethStakingView: cap(true),
          eventAnalysisView: cap(true),
          graphsView: cap(false),
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
          assetMovementMatching: cap(false),
          ethStakingView: cap(true),
          eventAnalysisView: cap(false),
          graphsView: cap(false),
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
          assetMovementMatching: cap(false),
          ethStakingView: cap(false),
          eventAnalysisView: cap(false),
          graphsView: cap(false),
        });

        const { isFeatureAllowed } = usePremiumHelper();
        const ethStakingAllowed = isFeatureAllowed(PremiumFeature.ETH_STAKING_VIEW);

        expect(get(ethStakingAllowed)).toBe(false);

        // Update capabilities
        set(capabilities, {
          assetMovementMatching: cap(false),
          ethStakingView: cap(true),
          eventAnalysisView: cap(false),
          graphsView: cap(false),
        });

        await nextTick();
        expect(get(ethStakingAllowed)).toBe(true);
      });

      it('should reactively update when premium status changes', async () => {
        const store = usePremiumStore();
        const { capabilities, premium } = storeToRefs(store);
        set(premium, true);
        set(capabilities, {
          assetMovementMatching: cap(true),
          ethStakingView: cap(true),
          eventAnalysisView: cap(true),
          graphsView: cap(true),
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

    describe('getFeatureMinimumTier', () => {
      it('should return the minimum tier for a feature', () => {
        const store = usePremiumStore();
        const { capabilities, premium } = storeToRefs(store);
        set(premium, true);
        set(capabilities, {
          assetMovementMatching: cap(false, 'Advanced'),
          ethStakingView: cap(true, 'Lite'),
          eventAnalysisView: cap(false, 'Advanced'),
          graphsView: cap(true, 'Basic'),
        });

        const { getFeatureMinimumTier } = usePremiumHelper();

        expect(get(getFeatureMinimumTier(PremiumFeature.ASSET_MOVEMENT_MATCHING))).toBe('Advanced');
        expect(get(getFeatureMinimumTier(PremiumFeature.ETH_STAKING_VIEW))).toBe('Lite');
        expect(get(getFeatureMinimumTier(PremiumFeature.GRAPHS_VIEW))).toBe('Basic');
      });

      it('should return empty string when capabilities are not loaded', () => {
        const { getFeatureMinimumTier } = usePremiumHelper();
        expect(get(getFeatureMinimumTier(PremiumFeature.ASSET_MOVEMENT_MATCHING))).toBe('');
      });
    });
  });

  describe('usePremiumStore - API Integration', () => {
    beforeEach(() => {
      const { logged } = storeToRefs(useSessionAuthStore());
      set(logged, true);
    });

    it('should fetch and parse capabilities when premium status becomes true', async () => {
      const mockCapabilities: PremiumCapabilities = {
        [PremiumFeature.ASSET_MOVEMENT_MATCHING]: cap(false, 'Advanced'),
        [PremiumFeature.ETH_STAKING_VIEW]: cap(true),
        [PremiumFeature.EVENT_ANALYSIS_VIEW]: cap(false),
        [PremiumFeature.GRAPHS_VIEW]: cap(true),
      };

      server.use(mockPremiumCapabilities(mockCapabilities));

      const store = usePremiumStore();
      const { capabilities, premium } = storeToRefs(store);

      // Trigger the watcher by setting premium to true
      set(premium, true);

      await vi.waitFor(() => {
        expect(get(capabilities)).toEqual(mockCapabilities);
      });
    });

    it('should handle API response with missing capabilities', async () => {
      // Simulate backend response missing some capabilities
      const partialCapabilities: Partial<PremiumCapabilities> = {
        [PremiumFeature.ETH_STAKING_VIEW]: cap(true),
        // Missing EVENT_ANALYSIS_VIEW and GRAPHS_VIEW
      };

      server.use(mockPremiumCapabilities<Partial<PremiumCapabilities>>(partialCapabilities));

      const store = usePremiumStore();
      const { premium } = storeToRefs(store);

      set(premium, true);

      const { isFeatureAllowed } = usePremiumHelper();

      await vi.waitFor(() => {
        expect(get(isFeatureAllowed(PremiumFeature.ETH_STAKING_VIEW))).toBe(true);
        expect(get(isFeatureAllowed(PremiumFeature.EVENT_ANALYSIS_VIEW))).toBe(false);
        expect(get(isFeatureAllowed(PremiumFeature.GRAPHS_VIEW))).toBe(false);
      });
    });

    it('should handle all capabilities set to false', async () => {
      const allFalseCapabilities: PremiumCapabilities = {
        [PremiumFeature.ASSET_MOVEMENT_MATCHING]: cap(false),
        [PremiumFeature.ETH_STAKING_VIEW]: cap(false),
        [PremiumFeature.EVENT_ANALYSIS_VIEW]: cap(false),
        [PremiumFeature.GRAPHS_VIEW]: cap(false),
      };

      server.use(mockPremiumCapabilities(allFalseCapabilities));

      const store = usePremiumStore();
      const { capabilities, premium } = storeToRefs(store);

      set(premium, true);

      await vi.waitFor(() => {
        expect(get(capabilities)).toEqual(allFalseCapabilities);
      });

      const { isFeatureAllowed } = usePremiumHelper();
      const ethStakingAllowed = isFeatureAllowed(PremiumFeature.ETH_STAKING_VIEW);
      const graphsAllowed = isFeatureAllowed(PremiumFeature.GRAPHS_VIEW);
      const eventAnalysisAllowed = isFeatureAllowed(PremiumFeature.EVENT_ANALYSIS_VIEW);

      expect(get(ethStakingAllowed)).toBe(false);
      expect(get(graphsAllowed)).toBe(false);
      expect(get(eventAnalysisAllowed)).toBe(false);
    });

    it('should handle API error gracefully', async () => {
      const apiCallSpy = vi.fn(() => HttpResponse.json({ message: 'Internal server error' }, { status: 500 }));

      server.use(
        http.get(`${backendUrl}/api/1/premium/capabilities`, apiCallSpy),
      );

      const store = usePremiumStore();
      const { capabilities, premium } = storeToRefs(store);

      set(premium, true);

      // Wait for API call to be attempted
      await vi.waitFor(() => {
        expect(apiCallSpy).toHaveBeenCalled();
      });

      // Capabilities should remain undefined on error
      expect(get(capabilities)).toBeUndefined();
    });

    it('should refetch capabilities when premium status becomes false', async () => {
      const mockCapabilities: PremiumCapabilities = {
        [PremiumFeature.ASSET_MOVEMENT_MATCHING]: cap(true),
        [PremiumFeature.ETH_STAKING_VIEW]: cap(true),
        [PremiumFeature.EVENT_ANALYSIS_VIEW]: cap(true),
        [PremiumFeature.GRAPHS_VIEW]: cap(true),
      };

      server.use(mockPremiumCapabilities(mockCapabilities));

      const store = usePremiumStore();
      const { capabilities, premium } = storeToRefs(store);

      // First set premium to true
      set(premium, true);
      await vi.waitFor(() => {
        expect(get(capabilities)).toEqual(mockCapabilities);
      });

      // Set it to false - capabilities should be refetched, not cleared
      set(premium, false);
      await vi.waitFor(() => {
        expect(get(capabilities)).toEqual(mockCapabilities);
      });
    });

    it('should not fetch capabilities if premium was already true', async () => {
      const mockCapabilities: PremiumCapabilities = {
        [PremiumFeature.ASSET_MOVEMENT_MATCHING]: cap(true),
        [PremiumFeature.ETH_STAKING_VIEW]: cap(true),
        [PremiumFeature.EVENT_ANALYSIS_VIEW]: cap(true),
        [PremiumFeature.GRAPHS_VIEW]: cap(true),
      };

      const apiCallSpy = vi.fn(() => HttpResponse.json<ActionResult<PremiumCapabilities>>({
        message: '',
        result: mockCapabilities,
      }, { status: 200 }));

      server.use(
        http.get(`${backendUrl}/api/1/premium/capabilities`, apiCallSpy),
      );

      const store = usePremiumStore();
      const { capabilities, premium } = storeToRefs(store);

      // Set premium to true initially
      set(premium, true);

      // Wait for capabilities to be fetched (includes initial watchImmediate call + set to true)
      await vi.waitFor(() => {
        expect(get(capabilities)).toEqual(mockCapabilities);
      });

      const callCount = apiCallSpy.mock.calls.length;

      // Set premium to true again (no change from true to true)
      set(premium, true);
      await nextTick();

      // Should not call API again since premium value didn't change
      expect(apiCallSpy).toHaveBeenCalledTimes(callCount);
    });

    it('should integrate with isFeatureAllowed after API call', async () => {
      const mockCapabilities: PremiumCapabilities = {
        [PremiumFeature.ASSET_MOVEMENT_MATCHING]: cap(false),
        [PremiumFeature.ETH_STAKING_VIEW]: cap(true),
        [PremiumFeature.EVENT_ANALYSIS_VIEW]: cap(false),
        [PremiumFeature.GRAPHS_VIEW]: cap(true),
      };

      server.use(mockPremiumCapabilities(mockCapabilities));

      const store = usePremiumStore();
      const { premium } = storeToRefs(store);
      const { isFeatureAllowed } = usePremiumHelper();

      const ethStakingAllowed = isFeatureAllowed(PremiumFeature.ETH_STAKING_VIEW);
      const graphsAllowed = isFeatureAllowed(PremiumFeature.GRAPHS_VIEW);
      const eventAnalysisAllowed = isFeatureAllowed(PremiumFeature.EVENT_ANALYSIS_VIEW);

      // Initially all should be false
      expect(get(ethStakingAllowed)).toBe(false);
      expect(get(graphsAllowed)).toBe(false);
      expect(get(eventAnalysisAllowed)).toBe(false);

      // Activate premium
      set(premium, true);

      // Wait for capabilities to be fetched and set
      await vi.waitFor(() => {
        expect(get(ethStakingAllowed)).toBe(true);
        expect(get(graphsAllowed)).toBe(true);
        expect(get(eventAnalysisAllowed)).toBe(false);
      });
    });
  });
});
