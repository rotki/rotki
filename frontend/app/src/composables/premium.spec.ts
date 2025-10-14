import type { ActionResult } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePremiumStore } from '@/store/session/premium';
import { type PremiumCapabilities, PremiumFeature } from '@/types/session';
import { usePremiumHelper } from './premium';

const backendUrl = process.env.VITE_BACKEND_URL;

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

  describe('usePremiumStore - API Integration', () => {
    it('should fetch and parse capabilities when premium status becomes true', async () => {
      const mockCapabilities: PremiumCapabilities = {
        [PremiumFeature.ETH_STAKING_VIEW]: true,
        [PremiumFeature.EVENT_ANALYSIS_VIEW]: false,
        [PremiumFeature.GRAPHS_VIEW]: true,
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

    it('should handle API response with missing capabilities (defaults to false)', async () => {
      // Simulate backend response missing some capabilities - zod will apply defaults
      const partialCapabilities: Partial<PremiumCapabilities> = {
        [PremiumFeature.ETH_STAKING_VIEW]: true,
        // Missing EVENT_ANALYSIS_VIEW and GRAPHS_VIEW - should default to false
      };

      server.use(mockPremiumCapabilities<Partial<PremiumCapabilities>>(partialCapabilities));

      const store = usePremiumStore();
      const { capabilities, premium } = storeToRefs(store);

      set(premium, true);

      await vi.waitFor(() => {
        const caps = get(capabilities);
        expect(caps?.[PremiumFeature.ETH_STAKING_VIEW]).toBe(true);
        expect(caps?.[PremiumFeature.EVENT_ANALYSIS_VIEW]).toBe(false);
        expect(caps?.[PremiumFeature.GRAPHS_VIEW]).toBe(false);
      });
    });

    it('should handle all capabilities set to false', async () => {
      const allFalseCapabilities: PremiumCapabilities = {
        [PremiumFeature.ETH_STAKING_VIEW]: false,
        [PremiumFeature.EVENT_ANALYSIS_VIEW]: false,
        [PremiumFeature.GRAPHS_VIEW]: false,
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

    it('should clear capabilities when premium status becomes false', async () => {
      const mockCapabilities: PremiumCapabilities = {
        [PremiumFeature.ETH_STAKING_VIEW]: true,
        [PremiumFeature.EVENT_ANALYSIS_VIEW]: true,
        [PremiumFeature.GRAPHS_VIEW]: true,
      };

      server.use(mockPremiumCapabilities(mockCapabilities));

      const store = usePremiumStore();
      const { capabilities, premium } = storeToRefs(store);

      // First set premium to true
      set(premium, true);
      await vi.waitFor(() => {
        expect(get(capabilities)).toEqual(mockCapabilities);
      });

      // Then set it to false
      set(premium, false);
      await nextTick();

      expect(get(capabilities)).toBeUndefined();
    });

    it('should not fetch capabilities if premium was already true', async () => {
      const mockCapabilities: PremiumCapabilities = {
        [PremiumFeature.ETH_STAKING_VIEW]: true,
        [PremiumFeature.EVENT_ANALYSIS_VIEW]: true,
        [PremiumFeature.GRAPHS_VIEW]: true,
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

      // Wait for first API call
      await vi.waitFor(() => {
        expect(apiCallSpy).toHaveBeenCalledTimes(1);
      });

      // Set premium to true again (no change from true to true)
      set(premium, true);
      await nextTick();

      // Wait to ensure no additional API call is made
      await vi.waitFor(() => {
        expect(get(capabilities)).toEqual(mockCapabilities);
      });

      // Should not call API again since premium was already true
      expect(apiCallSpy).toHaveBeenCalledTimes(1);
    });

    it('should integrate with isFeatureAllowed after API call', async () => {
      const mockCapabilities: PremiumCapabilities = {
        [PremiumFeature.ETH_STAKING_VIEW]: true,
        [PremiumFeature.EVENT_ANALYSIS_VIEW]: false,
        [PremiumFeature.GRAPHS_VIEW]: true,
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
