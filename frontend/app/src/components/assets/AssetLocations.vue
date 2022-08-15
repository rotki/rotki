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
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { computed, defineComponent, ref, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { CURRENCY_USD } from '@/data/currencies';
import i18n from '@/i18n';
import { useAssetInfoRetrieval } from '@/store/assets';
import { useBalancesStore } from '@/store/balances';
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';
import { AssetBreakdown } from '@/store/balances/types';
import { useMainStore } from '@/store/main';
import { useGeneralSettingsStore } from '@/store/settings/general';

type AssetLocations = (AssetBreakdown & {
  readonly account: GeneralAccount | undefined;
} & {
  readonly label: string;
})[];

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

    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
    const { getAccountByAddress, getEth2Account } =
      useBlockchainAccountsStore();
    const { detailsLoading } = storeToRefs(useMainStore());
    const { assetPriceInfo } = useAssetInfoRetrieval();
    const { assetBreakdown } = useBalancesStore();

    const onlyTags = ref<string[]>([]);

    const totalUsdValue = computed<BigNumber>(() => {
      return get(assetPriceInfo(get(identifier))).usdValue;
    });

    const getAccount = (item: AssetBreakdown) =>
      computed<GeneralAccount | undefined>(() => {
        if (item.location === Blockchain.ETH2) {
          return get(getEth2Account(item.address));
        }
        return get(getAccountByAddress(item.address));
      });

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

      const labelAccount = i18n.t('common.account').toString();
      const labelValidator = i18n
        .t('asset_locations.header.validator')
        .toString();

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
          text: i18n.t('common.location').toString(),
          value: 'location',
          align: 'center',
          width: '120px'
        },
        {
          text: label,
          value: 'label'
        },
        {
          text: i18n.t('common.amount').toString(),
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
    });

    return {
      onlyTags,
      tableHeaders,
      visibleAssetLocations,
      detailsLoading,
      getPercentage,
      getAccount
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
