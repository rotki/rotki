<script setup lang="ts">
import type { Exchange, ExchangeFormData } from '@/modules/balances/types/exchanges';
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { useTimeoutFn } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { definePage } from 'vue-router/experimental';
import { msg } from '@/message-key';
import ExchangeBalancesEmpty from '@/modules/balances/exchanges/ExchangeBalancesEmpty.vue';
import ExchangeConnectionsTable from '@/modules/balances/exchanges/ExchangeConnectionsTable.vue';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useExchangeConnectionsTable } from '@/modules/balances/exchanges/use-exchange-connections-table';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';
import ExchangeKeysFormDialog from '@/modules/settings/api-keys/exchange/ExchangeKeysFormDialog.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.accounts_sub.exchanges'), icon: 'lu-coins-exchange', parent: '/accounts/', heading: msg.$t('navigation_menu.accounts_sub.heading.exchanges_and_banks'), order: 60, drawer: 'accounts-exchanges', addAction: { labelKey: msg.$t('exchange_settings.dialog.add.title') } },
  },
});

const exchange = ref<ExchangeFormData>();

const { exchangesWithKey } = storeToRefs(useLocationStore());
const { removeExchange } = useExchanges();
const { connectedExchanges: rows } = storeToRefs(useConnectedExchangesStore());

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute('/accounts/exchanges/');

const { balanceOf, cols, highlight: highlightExchange, modelSort: sort, rowClass } = useExchangeConnectionsTable();

/**
 * A blank form, on the given exchange when it is one rotki can connect, otherwise on the first.
 *
 * @param location - the exchange to start on, as a link from another page names it
 */
function createNewExchange(location?: string): ExchangeFormData {
  const supported = get(exchangesWithKey);
  return {
    apiKey: '',
    apiSecret: '',
    binanceHistoryStartTs: undefined,
    binanceMarkets: undefined,
    gateLocation: 'global',
    krakenAccountType: 'starter',
    krakenFuturesApiKey: '',
    krakenFuturesApiSecret: '',
    location: location && supported.includes(location) ? location : supported[0],
    mode: 'add',
    name: '',
    newName: '',
    okxLocation: 'global',
    passphrase: '',
  };
}

const showSetupHint = ref<boolean>(false);
const { start: startHintTimeout, stop: stopHintTimeout } = useTimeoutFn(() => {
  set(showSetupHint, false);
}, 9000, { immediate: false });

function onExchangeAdded(exchange: { location: string; name: string }): void {
  highlightExchange(exchange);
  set(showSetupHint, true);
  stopHintTimeout();
  startHintTimeout();
}

function dismissSetupHint(): void {
  stopHintTimeout();
  set(showSetupHint, false);
}

function addExchange(location?: string): void {
  set(exchange, createNewExchange(location));
}

function editExchange(exchangePayload: Exchange) {
  set(exchange, {
    ...createNewExchange(),
    ...exchangePayload,
    mode: 'edit',
    newName: exchangePayload.name,
  });
}

const { deleteRow: removeRow, failure: removeFailure } = useTableRowDeletion<Exchange>({
  deleteItem: removeExchange,
  failureTitle: () => t('actions.balances.exchange_removal.title'),
});

watch(route, async (route) => {
  const { query } = route;

  if (query.add) {
    // `?add=true&location=kraken` opens the dialog on that exchange
    addExchange(typeof query.location === 'string' ? query.location : undefined);
    await router.replace({ query: {} });
  }
  else if (query.identifier || (query.location && query.name)) {
    const exchangeToEdit = get(rows).find(
      ex => (query.identifier ? ex.identifier === query.identifier : ex.location === query.location && ex.name === query.name),
    );
    if (exchangeToEdit) {
      editExchange(exchangeToEdit);
      await router.replace({ query: {} });
    }
  }
}, { immediate: true });
</script>

<template>
  <TablePageLayout
    class="exchange-settings"
    data-testid="exchanges"
    :title="[
      t('navigation_menu.accounts'),
      t('navigation_menu.accounts_sub.exchanges'),
    ]"
  >
    <template #buttons>
      <RuiButton
        color="primary"
        data-testid="add-exchange"
        @click="addExchange()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('exchange_balances.add_exchange') }}
      </RuiButton>
    </template>

    <FailureStrip
      v-if="removeFailure"
      class="mb-4"
      :title="removeFailure.title"
      :failure="removeFailure.failure"
      data-testid="exchange-remove-error"
    />

    <ExchangeBalancesEmpty
      v-if="rows.length === 0"
      @connect="addExchange($event)"
    />

    <ExchangeConnectionsTable
      v-else
      v-model:sort="sort"
      :rows="rows"
      :cols="cols"
      :show-setup-hint="showSetupHint"
      :row-class="rowClass"
      :balance-of="balanceOf"
      @dismiss-setup-hint="dismissSetupHint()"
      @edit="editExchange($event)"
      @delete="removeRow($event)"
    />

    <ExchangeKeysFormDialog
      v-model="exchange"
      @added="onExchangeAdded($event)"
    />
  </TablePageLayout>
</template>
