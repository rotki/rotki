<template>
  <card>
    <template #title>
      {{ t('asset_locations.title') }}
    </template>
    <template #actions>
      <v-row no-gutters justify="end">
        <v-col cols="12" md="6" lg="4">
          <tag-filter v-model="onlyTags" />
        </v-col>
      </v-row>
    </template>
    <data-table
      :headers="tableHeaders"
      :items="visibleAssetLocations"
      sort-by="balance.amount"
      :loading="detailsLoading"
    >
      <template #item.location="{ item }">
        <location-display
          :identifier="item.location"
          :detail-path="item.detailPath"
        />
      </template>
      <template #item.label="{ item }">
        <div class="py-4">
          <labeled-address-display
            v-if="item.account"
            :account="item.account"
          />
          <tag-display :tags="item.tags" />
        </div>
      </template>
      <template #item.balance.amount="{ item }">
        <amount-display :value="item.balance.amount" />
      </template>
      <template #item.balance.usdValue="{ item }">
        <amount-display
          show-currency="symbol"
          :amount="item.balance.amount"
          :price-asset="identifier"
          fiat-currency="USD"
          :value="item.balance.usdValue"
        />
      </template>
      <template #item.percentage="{ item }">
        <percentage-display :value="getPercentage(item.balance.usdValue)" />
      </template>
    </data-table>
  </card>
</template>

<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { ComputedRef } from 'vue';
import { DataTableHeader } from 'vuetify';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { useAggregatedBalancesStore } from '@/store/balances/aggregated';
import { useBalancesBreakdownStore } from '@/store/balances/breakdown';
import { AssetBreakdown } from '@/store/balances/types';
import { useAccountBalancesStore } from '@/store/blockchain/accountbalances';
import { useEthAccountsStore } from '@/store/blockchain/accounts/eth';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusStore } from '@/store/status';
import { CURRENCY_USD } from '@/types/currencies';

type AssetLocations = (AssetBreakdown & {
  readonly account: GeneralAccount | undefined;
} & {
  readonly label: string;
})[];

const props = defineProps({
  identifier: { required: true, type: String }
});

const { identifier } = toRefs(props);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { getAccountByAddress } = useAccountBalancesStore();
const { getEth2Account } = useEthAccountsStore();
const { detailsLoading } = storeToRefs(useStatusStore());
const { assetPriceInfo } = useAggregatedBalancesStore();
const { assetBreakdown } = useBalancesBreakdownStore();
const { t } = useI18n();

const onlyTags = ref<string[]>([]);

const totalUsdValue = computed<BigNumber>(() => {
  return get(assetPriceInfo(identifier)).usdValue;
});

const getAccount = (
  item: AssetBreakdown
): ComputedRef<GeneralAccount | undefined> =>
  computed(() =>
    item.location === Blockchain.ETH2
      ? get(getEth2Account(item.address))
      : get(getAccountByAddress(item.address))
  );

const assetLocations = computed<AssetLocations>(() => {
  const breakdowns = get(assetBreakdown(get(identifier)));
  return breakdowns.map((item: AssetBreakdown) => {
    const account = get(getAccount(item));
    return {
      ...item,
      account,
      label: account?.label ?? ''
    };
  });
});

const visibleAssetLocations = computed<AssetLocations>(() => {
  if (get(onlyTags).length === 0) {
    return get(assetLocations);
  }

  return get(assetLocations).filter(assetLocation => {
    if (assetLocation.tags) {
      return get(onlyTags).every(tag => assetLocation.tags?.includes(tag));
    }
  });
});

const getPercentage = (usdValue: BigNumber): string => {
  const percentage = get(totalUsdValue).isZero()
    ? 0
    : usdValue.div(get(totalUsdValue)).multipliedBy(100);

  return percentage.toFixed(2);
};

const tableHeaders = computed<DataTableHeader[]>(() => {
  const visibleItemsLength = get(visibleAssetLocations).length;
  const eth2Length = get(visibleAssetLocations).filter(
    account => account?.location === Blockchain.ETH2
  ).length;

  const labelAccount = t('common.account').toString();
  const labelValidator = t('asset_locations.header.validator').toString();

  let label = '';
  if (eth2Length === 0) {
    label = labelAccount;
  } else if (eth2Length === visibleItemsLength) {
    label = labelValidator;
  } else {
    label = `${labelAccount} / ${labelValidator}`;
  }

  return [
    {
      text: t('common.location').toString(),
      value: 'location',
      align: 'center',
      width: '120px'
    },
    {
      text: label,
      value: 'label'
    },
    {
      text: t('common.amount').toString(),
      value: 'balance.amount',
      align: 'end'
    },
    {
      text: t('asset_locations.header.value', {
        symbol: get(currencySymbol) ?? CURRENCY_USD
      }).toString(),
      value: 'balance.usdValue',
      align: 'end'
    },
    {
      text: t('asset_locations.header.percentage').toString(),
      value: 'percentage',
      sortable: false,
      align: 'end'
    }
  ];
});
</script>

<style scoped lang="scss">
:deep() {
  th {
    &:first-child {
      span {
        padding-left: 16px;
      }
    }
  }
}

.asset-locations-table {
  &__tag {
    margin-right: 8px;
    margin-bottom: 2px;
  }
}
</style>
