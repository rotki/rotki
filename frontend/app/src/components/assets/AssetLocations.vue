<template>
  <card>
    <template #title>
      {{ $t('asset_locations.title') }}
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
        <location-display :identifier="item.location" />
      </template>
      <template #item.label="{ item }">
        <div class="py-4">
          <labeled-address-display
            v-if="item.address"
            :account="account(item.address).value"
          />
          <tag-display :tags="item.tags" />
        </div>
      </template>
      <template #item.balance.amount="{ item }">
        <amount-display :value="item.balance.amount" />
      </template>
      <template #item.balance.usdValue="{ item }">
        <amount-display
          :fiat-currency="identifier"
          :amount="item.balance.amount"
          :value="item.balance.usdValue"
          show-currency="symbol"
        />
      </template>
      <template #item.percentage="{ item }">
        <percentage-display :value="getPercentage(item.balance.usdValue)" />
      </template>
    </data-table>
  </card>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { computed, defineComponent, ref, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { DataTableHeader } from 'vuetify';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { setupBlockchainAccounts } from '@/composables/balances';
import { setupGeneralSettings } from '@/composables/session';
import { CURRENCY_USD } from '@/data/currencies';
import i18n from '@/i18n';
import { useAssetInfoRetrieval } from '@/store/assets';
import { AssetBreakdown } from '@/store/balances/types';
import { useMainStore } from '@/store/store';
import { useStore } from '@/store/utils';

export default defineComponent({
  name: 'AssetLocations',
  components: {
    DataTable,
    LabeledAddressDisplay,
    TagDisplay,
    TagFilter
  },
  props: {
    identifier: { required: true, type: String }
  },
  setup(props) {
    const { identifier } = toRefs(props);

    const { currencySymbol } = setupGeneralSettings();
    const { account } = setupBlockchainAccounts();
    const { detailsLoading } = toRefs(useMainStore());
    const { assetPriceInfo } = useAssetInfoRetrieval();

    const store = useStore();

    const assetBreakdown = (asset: string) =>
      computed<AssetBreakdown[]>(() => {
        return store.getters['balances/assetBreakdown'](asset);
      });

    const tableHeaders: DataTableHeader[] = [
      {
        text: i18n.t('asset_locations.header.location').toString(),
        value: 'location',
        align: 'center',
        width: '120px'
      },
      {
        text: i18n.t('asset_locations.header.account').toString(),
        value: 'label'
      },
      {
        text: i18n.t('asset_locations.header.amount').toString(),
        value: 'balance.amount',
        align: 'end'
      },
      {
        text: i18n
          .t('asset_locations.header.value', {
            symbol: get(currencySymbol) ?? CURRENCY_USD
          })
          .toString(),
        value: 'balance.usdValue',
        align: 'end'
      },
      {
        text: i18n.t('asset_locations.header.percentage').toString(),
        value: 'percentage',
        sortable: false,
        align: 'end'
      }
    ];

    const onlyTags = ref<string[]>([]);

    const totalUsdValue = computed<BigNumber>(() => {
      return get(assetPriceInfo(get(identifier))).usdValue;
    });

    const assetLocations = computed<
      (AssetBreakdown & { readonly label: string })[]
    >(() => {
      return get(assetBreakdown(get(identifier))).map(value => ({
        label: get(account(value.address))?.label ?? '',
        ...value
      }));
    });

    const visibleAssetLocations = computed<
      (AssetBreakdown & { readonly label: string })[]
    >(() => {
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

    return {
      onlyTags,
      tableHeaders,
      visibleAssetLocations,
      detailsLoading,
      account,
      getPercentage
    };
  }
});
</script>

<style scoped lang="scss">
::v-deep {
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
