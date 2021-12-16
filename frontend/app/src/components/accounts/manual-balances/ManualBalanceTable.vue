<template>
  <card class="manual-balances" outlined-body :class="$style.table">
    <template #title>
      <refresh-button
        :loading="loading"
        :tooltip="$t('manual_balances_table.refresh.tooltip')"
        @refresh="refresh()"
      />
      <span>
        {{ title }}
      </span>
    </template>
    <template #actions>
      <v-row no-gutters justify="end">
        <v-col cols="12" md="6" lg="4">
          <tag-filter v-model="onlyTags" />
        </v-col>
      </v-row>
    </template>
    <data-table
      :loading="loading"
      :headers="headers"
      :items="visibleBalances"
      :item-class="getRowClass"
      class="manual-balances-list"
      sort-by="usdValue"
    >
      <template #item.label="{ item }">
        <div
          class="font-weight-medium"
          data-cy="label"
          :class="{
            'pt-0': !item.tags,
            [$style.label]: true
          }"
        >
          {{ item.label }}
        </div>
        <div>
          <tag-display :tags="item.tags" :small="true" />
        </div>
      </template>
      <template #item.asset="{ item }">
        <asset-details opens-details :asset="item.asset" />
      </template>
      <template #item.amount="{ item }">
        <amount-display
          class="manual-balances-list__amount"
          :value="item.amount"
        />
      </template>
      <template #item.usdValue="{ item }">
        <amount-display
          show-currency="symbol"
          :amount="item.amount"
          :fiat-currency="item.asset"
          :value="item.usdValue"
        />
      </template>
      <template #item.location="{ item }">
        <location-display
          class="manual-balances-list__location"
          :identifier="item.location"
          :data-cy="`manual-balances__location__${item.location}`"
        />
      </template>
      <template #item.actions="{ item }">
        <span>
          <v-icon
            small
            class="mr-2 manual-balances-list__actions__edit"
            @click="edit(item)"
          >
            mdi-pencil
          </v-icon>
          <v-icon
            small
            class="manual-balances-list__actions__delete"
            @click="pendingDeletion = item.label"
          >
            mdi-delete
          </v-icon>
        </span>
      </template>
      <template v-if="visibleBalances.length > 0" #body.append="{ isMobile }">
        <tr :class="$style.total">
          <td :colspan="isMobile ? 1 : 3">
            {{ $t('manual_balances_table.rows.total') }}
          </td>
          <td class="text-end">
            <amount-display
              show-currency="symbol"
              class="manual-balances-list__amount"
              :fiat-currency="currency"
              :value="total"
            />
          </td>
        </tr>
      </template>
    </data-table>
    <confirm-dialog
      v-if="pendingDeletion !== null"
      display
      :title="$t('manual_balances_table.delete_dialog.title')"
      :message="$t('manual_balances_table.delete_dialog.message')"
      @cancel="pendingDeletion = null"
      @confirm="deleteBalance()"
    />
  </card>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import {
  computed,
  defineComponent,
  PropType,
  Ref,
  ref,
  toRefs
} from '@vue/composition-api';
import { IVueI18n } from 'vue-i18n';
import { DataTableHeader } from 'vuetify';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import {
  setupExchangeRateGetter,
  setupManualBalances
} from '@/composables/balances';
import { currency } from '@/composables/session';
import { aggregateTotal } from '@/filters';
import i18n from '@/i18n';
import { ManualBalance } from '@/services/balances/types';
import { assert } from '@/utils/assertions';

const setupHeaders: (
  i18n: IVueI18n,
  currency: Ref<string>
) => Ref<DataTableHeader[]> = (i18n, currency) =>
  computed(() => [
    {
      text: i18n.t('manual_balances_table.columns.location').toString(),
      value: 'location',
      align: 'center',
      width: '120px'
    },
    {
      text: i18n.t('manual_balances_table.columns.label').toString(),
      value: 'label'
    },
    {
      text: i18n.t('manual_balances_table.columns.asset').toString(),
      value: 'asset',
      width: '200'
    },
    {
      text: i18n.t('manual_balances_table.columns.amount').toString(),
      value: 'amount',
      align: 'end'
    },
    {
      text: i18n
        .t('manual_balances_table.columns.value', {
          symbol: currency.value
        })
        .toString(),
      value: 'usdValue',
      align: 'end'
    },
    {
      text: i18n.t('manual_balances_table.columns.actions').toString(),
      value: 'actions',
      sortable: false,
      width: '50'
    }
  ]);

const ManualBalanceTable = defineComponent({
  name: 'ManualBalanceTable',
  components: { TagFilter, RefreshButton, TagDisplay },
  props: {
    title: { required: true, type: String },
    loading: { required: false, type: Boolean, default: false },
    balances: { required: true, type: Array as PropType<ManualBalance[]> }
  },
  emits: ['refresh', 'edit'],
  setup(props, { emit }) {
    const { balances } = toRefs(props);
    const pendingDeletion = ref<string | null>(null);
    const onlyTags = ref<string[]>([]);
    const refresh = () => {
      emit('refresh');
    };
    const edit = (balance: ManualBalance) => {
      emit('edit', balance);
    };

    const { deleteManualBalance } = setupManualBalances();

    const deleteBalance = async () => {
      const label = pendingDeletion.value;
      assert(label);
      pendingDeletion.value = null;
      await deleteManualBalance(label);
    };

    const visibleBalances = computed<ManualBalance[]>(() => {
      const selectedTags = onlyTags.value;
      if (selectedTags.length === 0) {
        return balances.value;
      }

      return balances.value.filter(balance => {
        if (balance.tags) {
          return selectedTags.every(tag => balance.tags.includes(tag));
        }
      });
    });

    const exchangeRate = setupExchangeRateGetter();

    const total = computed(() => {
      return aggregateTotal(
        visibleBalances.value,
        currency.value,
        exchangeRate(currency.value) ?? new BigNumber(1)
      );
    });

    const getRowClass = (item: ManualBalance) => {
      return `manual-balance__location__${item.location}`;
    };

    return {
      refresh,
      edit,
      deleteBalance,
      headers: setupHeaders(i18n, currency),
      onlyTags,
      total,
      currency,
      visibleBalances,
      getRowClass,
      pendingDeletion
    };
  }
});
export default ManualBalanceTable;
</script>

<style module lang="scss">
.total {
  font-weight: 500;
}

.label {
  padding-bottom: 0 !important;
}

.table {
  :global {
    th {
      &:first-child {
        span {
          padding-left: 16px;
        }
      }
    }
  }
}
</style>
