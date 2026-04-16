import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { WrapStatisticsResult } from '@/modules/statistics/api/use-wrap-statistics-api';
import { get } from '@vueuse/shared';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';

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
