<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type ComputedRef } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { CURRENCY_USD } from '@/types/currencies';
import { type AssetBreakdown } from '@/types/blockchain/accounts';
import { isBlockchain } from '@/types/blockchain/chains';

const props = defineProps<{ identifier: string }>();

const { t } = useI18n();

interface AssetLocation extends AssetBreakdown {
  readonly account?: GeneralAccount;
  readonly label: string;
}

type AssetLocations = AssetLocation[];

const { identifier } = toRefs(props);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { getAccountByAddress } = useAccountBalances();
const { getEth2Account } = useEthAccountsStore();
const { detailsLoading } = storeToRefs(useStatusStore());
const { assetPriceInfo } = useAggregatedBalances();
const { assetBreakdown } = useBalancesBreakdown();

const onlyTags = ref<string[]>([]);

const totalUsdValue = computed<BigNumber>(
  () => get(assetPriceInfo(identifier)).usdValue
);

const getAccount = (
  item: AssetBreakdown
): ComputedRef<GeneralAccount | undefined> =>
  computed(() =>
    item.location === Blockchain.ETH2
      ? get(getEth2Account(item.address))
      : get(getAccountByAddress(item.address, item.location))
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

const { addressNameSelector } = useAddressesNamesStore();

const visibleAssetLocations = computed<AssetLocations>(() => {
  const locations = get(assetLocations).map(item => ({
    ...item,
    label:
      (isBlockchain(item.location)
        ? get(addressNameSelector(item.address, item.location))
        : null) ||
      item.label ||
      item.address
  }));

  if (get(onlyTags).length === 0) {
    return locations;
  }

  return locations.filter(assetLocation => {
    const tags = assetLocation.tags ?? [];
    return get(onlyTags).every(tag => tags.includes(tag));
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

  let label: string;
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

<template>
  <Card>
    <template #title>
      {{ t('asset_locations.title') }}
    </template>
    <template #actions>
      <div class="flex justify-end">
        <div class="w-full md:w-[30rem]">
          <TagFilter v-model="onlyTags" />
        </div>
      </div>
    </template>
    <DataTable
      :headers="tableHeaders"
      :items="visibleAssetLocations"
      sort-by="balance.amount"
      :loading="detailsLoading"
    >
      <template #item.location="{ item }">
        <LocationDisplay
          :identifier="item.location"
          :detail-path="item.detailPath"
          class="py-2"
        />
      </template>
      <template #item.label="{ item }">
        <div class="py-4">
          <LabeledAddressDisplay v-if="item.account" :account="item.account" />
          <TagDisplay :tags="item.tags" small />
        </div>
      </template>
      <template #item.balance.amount="{ item }">
        <AmountDisplay :value="item.balance.amount" />
      </template>
      <template #item.balance.usdValue="{ item }">
        <AmountDisplay
          show-currency="symbol"
          :amount="item.balance.amount"
          :price-asset="identifier"
          fiat-currency="USD"
          :value="item.balance.usdValue"
        />
      </template>
      <template #item.percentage="{ item }">
        <PercentageDisplay :value="getPercentage(item.balance.usdValue)" />
      </template>
    </DataTable>
  </Card>
</template>

<style scoped lang="scss">
.asset-locations-table {
  &__tag {
    margin-right: 8px;
    margin-bottom: 2px;
  }
}
</style>
