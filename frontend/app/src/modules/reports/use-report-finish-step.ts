import type { Ref } from 'vue';
import type { EditableMissingPrice } from '@/modules/reports/report-types';
import {
  type FinishPrompt,
  summarizeMissingPrices,
  useMissingPriceFinishPrompt,
} from '@/modules/reports/use-report-actionable-items';

interface UseReportFinishStepOptions {
  /** Runs when the user accepts regenerating the report. */
  onRegenerate: () => void;
  /** Runs when the user accepts leaving the issues as they are. */
  onIgnore: () => void;
}

interface UseReportFinishStepReturn {
  /** The summary the card shows in place of its step actions, or `undefined` while not finishing. */
  prompt: Readonly<Ref<FinishPrompt | undefined>>;
  /** Shows the summary of how the missing prices were left. */
  ask: (missingPrices: EditableMissingPrice[]) => void;
  /** Goes back to the step, doing nothing. */
  cancel: () => void;
  /** Does what the summary offered: regenerate, or leave the issues. */
  accept: () => void;
}

/**
 * The actionable card's last step: a summary of the prices the user filled, asked in the card.
 *
 * @remarks
 * What accepting does depends on the summary, so the outcome is read from the prompt that was shown
 * rather than worked out again on accept.
 */
export function useReportFinishStep(options: UseReportFinishStepOptions): UseReportFinishStepReturn {
  const { onIgnore, onRegenerate } = options;
  const { promptFor } = useMissingPriceFinishPrompt();

  const prompt = shallowRef<FinishPrompt>();

  function ask(missingPrices: EditableMissingPrice[]): void {
    set(prompt, promptFor(summarizeMissingPrices(missingPrices)));
  }

  function cancel(): void {
    set(prompt, undefined);
  }

  function accept(): void {
    const shown = get(prompt);
    set(prompt, undefined);
    if (shown?.outcome === 'regenerate')
      onRegenerate();
    else if (shown)
      onIgnore();
  }

  return {
    accept,
    ask,
    cancel,
    prompt: readonly(prompt),
  };
}
