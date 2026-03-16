import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { WrapStatisticsResult } from '@/composables/api/statistics/wrap';
import { get } from '@vueuse/shared';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { useCurrencies } from '@/types/currencies';

interface GnosisPayResult {
  amount: BigNumber;
  code: string;
  name: string;
  symbol: string;
}

interface UseWrappedGnosisPayReturn {
  gnosisPayKey: ComputedRef<string | null>;
  gnosisPayResult: ComputedRef<GnosisPayResult[]>;
  showGnosisData: ComputedRef<boolean>;
}

export function useWrappedGnosisPay(summary: MaybeRefOrGetter<WrapStatisticsResult | null | undefined>): UseWrappedGnosisPayReturn {
  const { allowed } = useFeatureAccess(PremiumFeature.GNOSIS_PAY);
  const { getApiKey } = useExternalApiKeys();
  const { findCurrency } = useCurrencies();

  const gnosisPayKey = computed<string>(() => getApiKey('gnosis_pay'));
  const showGnosisData = computed<boolean>(() => get(allowed) && !!get(gnosisPayKey));

  const gnosisPayResult = computed<GnosisPayResult[]>(() => {
    const gnosisMaxPaymentsByCurrency = toValue(summary)?.gnosisMaxPaymentsByCurrency;
    if (!gnosisMaxPaymentsByCurrency) {
      return [];
    }

    const result: GnosisPayResult[] = [];

    for (const payment of gnosisMaxPaymentsByCurrency) {
      try {
        const currency = findCurrency(payment.symbol);
        if (currency) {
          result.push({
            amount: payment.amount,
            code: payment.symbol,
            name: currency.name,
            symbol: currency.unicodeSymbol,
          });
        }
      }
      catch {
        result.push({
          amount: payment.amount,
          code: payment.symbol,
          name: payment.symbol,
          symbol: payment.symbol,
        });
      }
    }

    return result;
  });

  return {
    gnosisPayKey,
    gnosisPayResult,
    showGnosisData,
  };
}
