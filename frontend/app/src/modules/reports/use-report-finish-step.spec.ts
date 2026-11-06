import type { EditableMissingPrice } from '@/modules/reports/report-types';
import { describe, expect, it, vi } from 'vitest';
import { useReportFinishStep } from '@/modules/reports/use-report-finish-step';

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

function setup(): ReturnType<typeof useReportFinishStep> & {
  onIgnore: ReturnType<typeof vi.fn<() => void>>;
  onRegenerate: ReturnType<typeof vi.fn<() => void>>;
} {
  const onIgnore = vi.fn<() => void>();
  const onRegenerate = vi.fn<() => void>();
  return { ...useReportFinishStep({ onIgnore, onRegenerate }), onIgnore, onRegenerate };
}

describe('useReportFinishStep', () => {
  it('should show the summary without acting on it yet', () => {
    const { ask, onIgnore, onRegenerate, prompt } = setup();

    ask([missingPrice('10')]);

    expect(get(prompt)).toMatchObject({ outcome: 'regenerate' });
    expect(onRegenerate).not.toHaveBeenCalled();
    expect(onIgnore).not.toHaveBeenCalled();
  });

  it('should regenerate on accept when prices were filled', () => {
    const { accept, ask, onIgnore, onRegenerate, prompt } = setup();
    ask([missingPrice('10'), missingPrice('')]);

    accept();

    expect(onRegenerate).toHaveBeenCalledOnce();
    expect(onIgnore).not.toHaveBeenCalled();
    expect(get(prompt)).toBeUndefined();
  });

  it('should leave the issues on accept when nothing was filled', () => {
    const { accept, ask, onIgnore, onRegenerate } = setup();
    ask([missingPrice('')]);

    accept();

    expect(onIgnore).toHaveBeenCalledOnce();
    expect(onRegenerate).not.toHaveBeenCalled();
  });

  it('should go back to the step, doing nothing, on cancel', () => {
    const { ask, cancel, onIgnore, onRegenerate, prompt } = setup();
    ask([missingPrice('10')]);

    cancel();

    expect(get(prompt)).toBeUndefined();
    expect(onRegenerate).not.toHaveBeenCalled();
    expect(onIgnore).not.toHaveBeenCalled();
  });

  it('should do nothing on an accept with no summary showing', () => {
    const { accept, onIgnore, onRegenerate } = setup();

    accept();

    expect(onRegenerate).not.toHaveBeenCalled();
    expect(onIgnore).not.toHaveBeenCalled();
  });
});
