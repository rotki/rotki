<script setup lang="ts">
import type { HistoricalAssetBalance, HistoricalBalancesResponse } from '@/types/balances';
import { type AssetBalanceWithPrice, bigNumberify, NoPrice } from '@rotki/common';
import dayjs from 'dayjs';
import AssetBalances from '@/components/AssetBalances.vue';
import GetPremiumPlaceholder from '@/components/common/GetPremiumPlaceholder.vue';
import HistoryEventsAlert from '@/components/history/HistoryEventsAlert.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useHistoricalBalancesApi } from '@/composables/api/balances/historical-balances-api';
import { summarizeAssetProtocols } from '@/composables/balances/asset-summary';
import { usePremium } from '@/composables/premium';
import { useCollectionInfo } from '@/modules/assets/use-collection-info';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';

const model = defineModel<boolean>({ required: true });

const { t } = useI18n({ useScope: 'global' });
const premium = usePremium();

const timestamp = ref<number>(dayjs().unix());
const selectedAsset = ref<string>();
const loading = ref<boolean>(false);
const errorMessage = ref<string>();
const balances = ref<AssetBalanceWithPrice[]>([]);

const { fetchHistoricalBalances } = useHistoricalBalancesApi();
const { isAssetIgnored } = useIgnoredAssetsStore();
const { useCollectionId, useCollectionMainAsset } = useCollectionInfo();

const hasResults = computed<boolean>(() => get(balances).length > 0);

function transformToAssetBalances(response: HistoricalBalancesResponse): AssetBalanceWithPrice[] {
  const sources: Record<string, Record<string, { amount: ReturnType<typeof bigNumberify>; value: ReturnType<typeof bigNumberify> }>> = {};

  for (const [asset, balance] of Object.entries(response)) {
    const amount = bigNumberify(balance.amount);
    const price = bigNumberify(balance.price);
    const value = amount.multipliedBy(price);

    sources[asset] = {
      historical: { amount, value },
    };
  }

  return summarizeAssetProtocols(
    {
      associatedAssets: {},
      sources: { historical: sources },
    },
    {
      hideIgnored: false,
      isAssetIgnored,
    },
    {
      getAssetPrice: (asset: string) => {
        const balance = response[asset];
        return balance ? bigNumberify(balance.price) : NoPrice;
      },
      noPrice: NoPrice,
    },
    {
      groupCollections: true,
      useCollectionId,
      useCollectionMainAsset,
    },
  );
}

async function fetchBalances(): Promise<void> {
  set(loading, true);
  set(errorMessage, undefined);
  set(balances, []);

  try {
    const asset = get(selectedAsset);
    const payload = {
      timestamp: get(timestamp),
      ...(asset ? { asset } : {}),
    };

    const response = await fetchHistoricalBalances(payload);

    let responseAsRecord: HistoricalBalancesResponse;
    if (asset) {
      responseAsRecord = { [asset]: response as HistoricalAssetBalance };
    }
    else {
      responseAsRecord = response as HistoricalBalancesResponse;
    }

    const transformedBalances = transformToAssetBalances(responseAsRecord);
    set(balances, transformedBalances);
  }
  catch (error: any) {
    if (error.message?.includes('404') || error.message?.includes('No historical data'))
      set(errorMessage, t('historical_balances_dialog.no_data'));
    else
      set(errorMessage, error.message);
  }
  finally {
    set(loading, false);
  }
}

function reset(): void {
  set(timestamp, dayjs().unix());
  set(selectedAsset, undefined);
  set(balances, []);
  set(errorMessage, undefined);
}

watch(model, (value) => {
  if (!value)
    reset();
});
</script>

<template>
  <RuiDialog
    v-model="model"
    max-width="800"
  >
    <RuiCard>
      <template #header>
        {{ t('historical_balances_dialog.title') }}
      </template>
      <template #subheader>
        {{ t('historical_balances_dialog.hint') }}
      </template>

      <GetPremiumPlaceholder
        v-if="!premium"
        :title="t('historical_balances_dialog.title')"
        :description="t('historical_balances_dialog.premium_required')"
      />

      <template v-else>
        <div class="flex flex-col gap-4">
          <HistoryEventsAlert />

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <DateTimePicker
              v-model="timestamp"
              variant="outlined"
              :label="t('historical_balances_dialog.timestamp_label')"
              max-date="now"
              type="epoch"
              accuracy="second"
            />

            <AssetSelect
              v-model="selectedAsset"
              clearable
              variant="outlined"
              :hint="t('historical_balances_dialog.asset_hint')"
            />
          </div>

          <RuiButton
            color="primary"
            :loading="loading"
            size="lg"
            @click="fetchBalances()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-search"
                size="20"
              />
            </template>
            {{ t('historical_balances_dialog.fetch_button') }}
          </RuiButton>

          <RuiAlert
            v-if="errorMessage"
            type="error"
          >
            {{ errorMessage }}
          </RuiAlert>

          <template v-if="hasResults">
            <RuiDivider class="my-2" />

            <AssetBalances
              :balances="balances"
              :loading="loading"
              hide-total
              class="table-inside-dialog !max-h-[calc(100vh-30rem)]"
              hide-breakdown
            />
          </template>
        </div>
      </template>

      <template #footer>
        <div class="w-full" />
        <RuiButton
          color="primary"
          variant="text"
          @click="model = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
