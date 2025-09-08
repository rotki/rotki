import type { BigNumber } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { WrapStatisticsResult } from '@/composables/api/statistics/wrap';
import { get } from '@vueuse/shared';
import { usePremium } from '@/composables/premium';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
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

export function useWrappedGnosisPay(summary: Ref<WrapStatisticsResult | null | undefined>): UseWrappedGnosisPayReturn {
  const { t } = useI18n({ useScope: 'global' });
  const premium = usePremium();
  const { apiKey } = useExternalApiKeys(t);
  const { findCurrency } = useCurrencies();

  const gnosisPayKey = computed<string | null>(() => get(apiKey('gnosis_pay')));
  const showGnosisData = computed<boolean>(() => get(premium) && !!get(gnosisPayKey));

  const gnosisPayResult = computed<GnosisPayResult[]>(() => {
    const gnosisMaxPaymentsByCurrency = get(summary)?.gnosisMaxPaymentsByCurrency;
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
