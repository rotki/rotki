import type { Component } from 'vue';
import type {
  EditableMissingPrice,
  MissingAcquisition,
  MissingPrice,
} from '@/modules/reports/report-types';
import { One, Zero } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  summarizeMissingPrices,
  useMissingPriceFinishPrompt,
  useReportActionableStepper,
} from '@/modules/reports/use-report-actionable-items';

function missingPrice(price: string): EditableMissingPrice {
  return {
    fromAsset: 'ETH',
    price,
    saved: false,
    time: 1,
    toAsset: 'EUR',
    useRefreshedHistoricalPrice: false,
  };
}

function acquisitions(count: number): MissingAcquisition[] {
  return Array.from({ length: count }, (_, index) => ({
    asset: 'ETH',
    foundAmount: Zero,
    missingAmount: One,
    originatingEventId: index,
    time: index,
  }));
}

function prices(count: number): MissingPrice[] {
  return Array.from({ length: count }, (_, index) => ({
    fromAsset: 'ETH',
    time: index,
    toAsset: 'EUR',
  }));
}

const selectors: Record<'missingAcquisitions' | 'missingPrices', Component> = {
  missingAcquisitions: { name: 'MissingAcquisitionsStub', template: '<div />' },
  missingPrices: { name: 'MissingPricesStub', template: '<div />' },
};

describe('summarizeMissingPrices', () => {
  it('should count a price the user entered as filled', () => {
    expect(summarizeMissingPrices([missingPrice('100'), missingPrice('200')])).toEqual({
      filled: 2,
      skipped: 0,
      total: 2,
    });
  });

  it('should count an empty price as skipped', () => {
    expect(summarizeMissingPrices([missingPrice('100'), missingPrice('')])).toEqual({
      filled: 1,
      skipped: 1,
      total: 2,
    });
  });

  /** The price is the text of a field, so "0" is something the user typed rather than a blank. */
  it('should count a zero price as filled', () => {
    expect(summarizeMissingPrices([missingPrice('0')])).toEqual({ filled: 1, skipped: 0, total: 1 });
  });

  it('should summarize an empty list', () => {
    expect(summarizeMissingPrices([])).toEqual({ filled: 0, skipped: 0, total: 0 });
  });
});

describe('useMissingPriceFinishPrompt', () => {
  it('should offer to regenerate when every price was filled', () => {
    const { promptFor } = useMissingPriceFinishPrompt();

    const prompt = promptFor({ filled: 3, skipped: 0, total: 3 });

    expect(prompt.type).toBe('success');
    expect(prompt.outcome).toBe('regenerate');
    expect(prompt.title).toBe('profit_loss_report.actionable.missing_prices.all_prices_filled');
  });

  it('should warn but still offer to regenerate when some were skipped', () => {
    const { promptFor } = useMissingPriceFinishPrompt();

    const prompt = promptFor({ filled: 2, skipped: 1, total: 3 });

    expect(prompt.type).toBe('warning');
    expect(prompt.outcome).toBe('regenerate');
    expect(prompt.title).toBe('profit_loss_report.actionable.missing_prices.total_skipped_prices::1');
  });

  /**
   * Regenerating a report that would come back identical is the wrong offer, so with nothing
   * filled in the prompt asks to dismiss the issues instead.
   */
  it('should offer to ignore the issues when nothing was filled', () => {
    const { promptFor } = useMissingPriceFinishPrompt();

    const prompt = promptFor({ filled: 0, skipped: 3, total: 3 });

    expect(prompt.type).toBe('warning');
    expect(prompt.outcome).toBe('ignore');
    expect(prompt.primaryAction).toBe('common.actions.yes');
    expect(prompt.title).toBe('profit_loss_report.actionable.missing_prices.no_filled_prices');
  });

  it('should offer to ignore when there was nothing to fill in at all', () => {
    const { promptFor } = useMissingPriceFinishPrompt();

    expect(promptFor({ filled: 0, skipped: 0, total: 0 }).outcome).toBe('ignore');
  });
});

describe('useReportActionableStepper', () => {
  describe('counting what the report left', () => {
    it('should count both kinds and their total', () => {
      const { counts } = useReportActionableStepper(
        { missingAcquisitions: acquisitions(2), missingPrices: prices(3) },
        selectors,
      );

      expect(get(counts)).toEqual({ missingAcquisitionsLength: 2, missingPricesLength: 3, total: 5 });
    });

    it('should count nothing before a report has been generated', () => {
      const { counts } = useReportActionableStepper(undefined, selectors);

      expect(get(counts)).toEqual({ missingAcquisitionsLength: 0, missingPricesLength: 0, total: 0 });
    });
  });

  describe('the steps it offers', () => {
    it('should offer a step for each kind that has something to show', () => {
      const { steps } = useReportActionableStepper(
        { missingAcquisitions: acquisitions(1), missingPrices: prices(1) },
        selectors,
      );

      expect(get(steps).map(step => step.key)).toEqual(['missingAcquisitions', 'missingPrices']);
    });

    it('should skip the acquisitions step when there are none', () => {
      const { steps } = useReportActionableStepper(
        { missingAcquisitions: [], missingPrices: prices(2) },
        selectors,
      );

      expect(get(steps).map(step => step.key)).toEqual(['missingPrices']);
    });

    it('should skip the prices step when there are none', () => {
      const { steps } = useReportActionableStepper(
        { missingAcquisitions: acquisitions(2), missingPrices: [] },
        selectors,
      );

      expect(get(steps).map(step => step.key)).toEqual(['missingAcquisitions']);
    });

    it('should offer no steps before a report has been generated', () => {
      const { steps } = useReportActionableStepper(undefined, selectors);

      expect(get(steps)).toEqual([]);
    });

    it('should give a step the items and the component that shows them', () => {
      const missingPrices = prices(2);
      const { steps } = useReportActionableStepper({ missingAcquisitions: [], missingPrices }, selectors);

      expect(get(steps)[0]).toMatchObject({
        items: missingPrices,
        selector: selectors.missingPrices,
      });
    });
  });

  describe('which step is showing', () => {
    it('should start on the first step', () => {
      const { modelStep } = useReportActionableStepper(
        { missingAcquisitions: acquisitions(1), missingPrices: prices(1) },
        selectors,
      );

      expect(get(modelStep)).toBe(1);
    });

    it('should stay where it is put while both kinds have something', () => {
      const { modelStep } = useReportActionableStepper(
        { missingAcquisitions: acquisitions(1), missingPrices: prices(1) },
        selectors,
      );

      set(modelStep, 2);

      expect(get(modelStep)).toBe(2);
    });

    /**
     * A second step that no longer exists would leave the stepper showing an empty panel, so the
     * step comes back to the first as soon as one of the two kinds is emptied.
     */
    it('should return to the first step once only one kind is left', async () => {
      const items = ref({ missingAcquisitions: acquisitions(1), missingPrices: prices(1) });
      const { modelStep } = useReportActionableStepper(items, selectors);

      set(modelStep, 2);
      set(items, { missingAcquisitions: acquisitions(1), missingPrices: [] });
      await nextTick();

      expect(get(modelStep)).toBe(1);
    });
  });
});
