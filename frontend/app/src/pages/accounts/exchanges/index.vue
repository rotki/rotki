<script setup lang="ts">
import type { Exchange, ExchangeFormData } from '@/modules/balances/types/exchanges';
import { externalLinks } from '@shared/external-links';
import { msg } from '@/message-key';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import ExchangeBalancesEmpty from '@/modules/balances/exchanges/ExchangeBalancesEmpty.vue';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useExchangeConnectionsTable } from '@/modules/balances/exchanges/use-exchange-connections-table';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useNonSyncingExchanges } from '@/modules/balances/exchanges/use-non-syncing-exchanges';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useLocations } from '@/modules/core/common/use-locations';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import ExchangeKeysFormDialog from '@/modules/settings/api-keys/exchange/ExchangeKeysFormDialog.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
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
const { show } = useConfirmStore();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute('/accounts/exchanges/');
const { getExchangeName } = useLocations();
const { isNonSyncExchange, resetNonSyncingExchanges, toggleSync } = useNonSyncingExchanges();

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

async function remove(item: Exchange) {
  await removeExchange(item);
}

function showRemoveConfirmation(item: Exchange) {
  show({
    message: t('exchange_settings.confirmation.message', {
      location: item ? getExchangeName(item.location) : '',
      name: item?.name ?? '',
    }),
    title: t('exchange_settings.confirmation.title'),
  }, () => remove(item));
}

onBeforeMount(() => {
  resetNonSyncingExchanges();
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

    <ExchangeBalancesEmpty
      v-if="rows.length === 0"
      @connect="addExchange($event)"
    />

    <TableFrame v-else>
      <template #toolbar>
        <div
          v-if="showSetupHint"
          class="flex items-center gap-2 flex-1 min-w-0 text-sm text-rui-text-secondary"
          data-testid="exchange-setup-hint"
        >
          <RuiIcon
            name="lu-info"
            size="16"
            class="text-rui-info shrink-0"
          />
          <span class="min-w-0">{{ t('exchange_settings.setup_hint') }}</span>
          <RuiButton
            variant="text"
            icon
            size="sm"
            class="shrink-0"
            :aria-label="t('common.actions.close')"
            @click="dismissSetupHint()"
          >
            <RuiIcon
              name="lu-x"
              size="14"
            />
          </RuiButton>
        </div>
        <i18n-t
          v-else
          scope="global"
          keypath="exchange_settings.subtitle"
          tag="p"
          class="flex-1 min-w-0 text-sm text-rui-text-secondary"
        >
          <ExternalLink
            :text="t('exchange_settings.usage_guide')"
            :url="externalLinks.usageGuideSection.addingAnExchange"
          />
        </i18n-t>
      </template>

      <RuiDataTable
        v-model:sort="sort"
        row-attr="identifier"
        data-testid="exchange-table"
        :rows="rows"
        :cols="cols"
        :item-class="rowClass"
      >
        <template #item.location="{ row }">
          <LocationDisplay
            :identifier="row.location"
            horizontal
            size="24px"
          />
        </template>
        <template #item.syncEnabled="{ row }">
          <RuiSwitch
            color="primary"
            :model-value="!isNonSyncExchange(row)"
            details="hidden"
            @update:model-value="toggleSync(row)"
          />
        </template>
        <template #item.balance="{ row }">
          <FiatDisplay
            :value="balanceOf(row)"
            class="font-medium tabular-nums"
            data-testid="exchange-balance"
          />
        </template>
        <template #item.actions="{ row }">
          <RowActions
            align="end"
            :delete-tooltip="t('exchange_settings.delete.tooltip')"
            :edit-tooltip="t('exchange_settings.edit.tooltip')"
            @delete-click="showRemoveConfirmation(row)"
            @edit-click="editExchange(row)"
          />
        </template>
      </RuiDataTable>
    </TableFrame>

    <ExchangeKeysFormDialog
      v-model="exchange"
      @added="onExchangeAdded($event)"
    />
  </TablePageLayout>
</template>
