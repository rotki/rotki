import type { Component, ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { DialogType } from '@/modules/core/common/dialogs';
import type {
  EditableMissingPrice,
  MissingAcquisition,
  MissingPrice,
} from '@/modules/reports/report-types';
import { toSentenceCase } from '@rotki/common';

/** The two kinds of issue a report can leave for the user to act on. */
export type ActionableStepKey = 'missingAcquisitions' | 'missingPrices';

/** What the report left outstanding, absent until a report has been generated. */
interface ActionableItems {
  readonly missingAcquisitions: MissingAcquisition[];
  readonly missingPrices: MissingPrice[];
}

interface ActionableCounts {
  readonly missingAcquisitionsLength: number;
  readonly missingPricesLength: number;
  readonly total: number;
}

/** One step of the card, which is only present when it has something to show. */
interface ActionableStep {
  readonly key: ActionableStepKey;
  readonly title: string;
  readonly hint: string;
  readonly selector: Component;
  readonly items: MissingAcquisition[] | MissingPrice[];
}

interface UseReportActionableStepperReturn {
  /** Which step is showing; the stepper's own controls move it. */
  modelStep: Ref<number>;
  /** How much of each kind the report left, which the header counts. */
  counts: ComputedRef<ActionableCounts>;
  /** The steps that have something to show, in order. */
  steps: ComputedRef<ActionableStep[]>;
}

/** How the user left the missing prices they were asked to fill in. */
export interface MissingPriceSummary {
  readonly total: number;
  readonly filled: number;
  readonly skipped: number;
}

/** The confirmation shown after the prices were submitted, and what confirming it does. */
export interface FinishPrompt {
  readonly type: DialogType;
  readonly title: string;
  readonly message: string;
  readonly primaryAction: string;
  /** Regenerating is only worth offering when something was actually filled in. */
  readonly outcome: 'regenerate' | 'ignore';
}

/**
 * Counts how the missing prices were left, since what the confirmation says depends on it.
 *
 * @param missingPrices - the rows as the form last had them
 * @returns how many there were, how many carry a price, and how many were skipped
 */
export function summarizeMissingPrices(missingPrices: EditableMissingPrice[]): MissingPriceSummary {
  const total = missingPrices.length;
  const filled = missingPrices.filter(missingPrice => !!missingPrice.price).length;
  return { filled, skipped: total - filled, total };
}

/**
 * The confirmation the card shows once the missing prices are submitted.
 *
 * @returns the prompt for a given summary
 */
export function useMissingPriceFinishPrompt(): { promptFor: (summary: MissingPriceSummary) => FinishPrompt } {
  const { t } = useI18n({ useScope: 'global' });

  function promptFor(summary: MissingPriceSummary): FinishPrompt {
    const nudge = t('profit_loss_report.actionable.missing_prices.regenerate_report_nudge');

    if (summary.filled === 0) {
      return {
        message: t('profit_loss_report.actionable.missing_prices.skipped_all_events_confirmation'),
        outcome: 'ignore',
        primaryAction: t('common.actions.yes'),
        title: t('profit_loss_report.actionable.missing_prices.no_filled_prices'),
        type: 'warning',
      };
    }

    const regenerate = {
      outcome: 'regenerate',
      primaryAction: t('profit_loss_report.actionable.actions.regenerate_report'),
    } as const;

    if (summary.skipped > 0) {
      return {
        ...regenerate,
        message: `${t('profit_loss_report.actionable.missing_prices.if_sure')} ${nudge}`,
        title: t('profit_loss_report.actionable.missing_prices.total_skipped_prices', {
          total: summary.skipped,
        }),
        type: 'warning',
      };
    }

    return {
      ...regenerate,
      message: toSentenceCase(nudge),
      title: t('profit_loss_report.actionable.missing_prices.all_prices_filled'),
      type: 'success',
    };
  }

  return { promptFor };
}

/**
 * The card's steps: one per kind of issue the report left, skipping a kind with nothing in it.
 *
 * @remarks
 * The step returns to the first whenever only one kind is left, so a stepper standing on a second
 * step that no longer exists does not show an empty panel.
 *
 * @param actionableItems - what the report left outstanding
 * @param selectors - the component each kind is shown with
 * @returns the current step, the counts and the steps to render
 */
export function useReportActionableStepper(
  actionableItems: MaybeRefOrGetter<ActionableItems | undefined>,
  selectors: Record<ActionableStepKey, Component>,
): UseReportActionableStepperReturn {
  const { t } = useI18n({ useScope: 'global' });

  const modelStep = shallowRef<number>(1);

  const counts = computed<ActionableCounts>(() => {
    const items = toValue(actionableItems);
    const missingAcquisitionsLength = items?.missingAcquisitions.length ?? 0;
    const missingPricesLength = items?.missingPrices.length ?? 0;

    return {
      missingAcquisitionsLength,
      missingPricesLength,
      total: missingAcquisitionsLength + missingPricesLength,
    };
  });

  const steps = computed<ActionableStep[]>(() => {
    const items = toValue(actionableItems);
    const { missingAcquisitionsLength, missingPricesLength } = get(counts);
    const contents: ActionableStep[] = [];

    if (items && missingAcquisitionsLength > 0) {
      contents.push({
        hint: t('profit_loss_report.actionable.missing_acquisitions.hint'),
        items: items.missingAcquisitions,
        key: 'missingAcquisitions',
        selector: selectors.missingAcquisitions,
        title: t('profit_loss_report.actionable.missing_acquisitions.title', {
          total: missingAcquisitionsLength,
        }),
      });
    }

    if (items && missingPricesLength > 0) {
      contents.push({
        hint: t('profit_loss_report.actionable.missing_prices.hint'),
        items: items.missingPrices,
        key: 'missingPrices',
        selector: selectors.missingPrices,
        title: t('profit_loss_report.actionable.missing_prices.title', {
          total: missingPricesLength,
        }),
      });
    }

    return contents;
  });

  watchImmediate(counts, ({ missingAcquisitionsLength, missingPricesLength }) => {
    if (!missingAcquisitionsLength || !missingPricesLength)
      set(modelStep, 1);
  });

  return { counts, modelStep, steps };
}
