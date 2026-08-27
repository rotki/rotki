<script setup lang="ts">
import type { DataTableColumn, DataTableSortColumn } from '@rotki/ui-library';
import type { Exchange, ExchangeFormData } from '@/modules/balances/types/exchanges';
import { externalLinks } from '@shared/external-links';
import { msg } from '@/message-key';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useLocations } from '@/modules/core/common/use-locations';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useRowHighlight } from '@/modules/core/table/use-row-highlight';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import ExchangeKeysFormDialog from '@/modules/settings/api-keys/exchange/ExchangeKeysFormDialog.vue';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.api_keys_sub.exchanges'), icon: 'lu-coins-exchange', parent: '/api-keys/', order: 20, drawer: 'api-keys-exchanges', addAction: { labelKey: msg.$t('exchange_settings.dialog.add.title') } },
  },
});

const nonSyncingExchanges = ref<Exchange[]>([]);
const exchange = ref<ExchangeFormData>();
const sort = ref<DataTableSortColumn<Exchange>>({
  column: 'name',
  direction: 'asc',
});

const { exchangesWithKey } = storeToRefs(useLocationStore());
const { removeExchange } = useExchanges();
const { connectedExchanges: rows } = storeToRefs(useConnectedExchangesStore());
const current = useSetting('nonSyncingExchanges');
const { update } = useSettingsOperations();
const { show } = useConfirmStore();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute('/api-keys/exchanges/');
const { getExchangeName } = useLocations();
const { notify } = useNotificationDispatcher();

const cols = computed<DataTableColumn<Exchange>[]>(() => [{
  align: 'center',
  cellClass: 'py-0 w-32',
  key: 'location',
  label: t('common.location'),
  sortable: true,
}, {
  key: 'name',
  label: t('common.name'),
  sortable: true,
}, {
  cellClass: 'w-32',
  key: 'syncEnabled',
  label: t('exchange_settings.header.sync_enabled'),
}, {
  align: 'center',
  cellClass: 'w-32',
  key: 'actions',
  label: t('common.actions_text'),
}]);

useRememberTableSorting<Exchange>(TableId.EXCHANGE, sort, cols);

function createNewExchange(): ExchangeFormData {
  return {
    apiKey: '',
    apiSecret: '',
    binanceHistoryStartTs: undefined,
    binanceMarkets: undefined,
    gateLocation: 'global',
    krakenAccountType: 'starter',
    krakenFuturesApiKey: '',
    krakenFuturesApiSecret: '',
    location: get(exchangesWithKey)[0],
    mode: 'add',
    name: '',
    newName: '',
    okxLocation: 'global',
    passphrase: '',
  };
}

function findNonSyncExchangeIndex(exchange: Exchange) {
  return get(nonSyncingExchanges).findIndex(
    (item: Exchange) => item.name === exchange.name && item.location === exchange.location,
  );
}

function isNonSyncExchange(exchange: Exchange) {
  return findNonSyncExchangeIndex(exchange) > -1;
}

function resetNonSyncingExchanges() {
  set(nonSyncingExchanges, get(current));
}

async function toggleSync(exchange: Exchange) {
  const index = findNonSyncExchangeIndex(exchange);

  const data = [...get(nonSyncingExchanges)];

  let enable = true;

  if (index > -1) {
    enable = false;
    data.splice(index);
  }
  else {
    data.push({ location: exchange.location, name: exchange.name });
  }

  const status = await update({
    nonSyncingExchanges: data,
  });

  if (!status.success) {
    notify({
      display: true,
      message: t('exchange_settings.sync.messages.description', {
        action: enable ? t('exchange_settings.sync.messages.enable') : t('exchange_settings.sync.messages.disable'),
        location: exchange.location,
        message: status.message,
        name: exchange.name,
      }),
      title: t('exchange_settings.sync.messages.title'),
    });
  }

  resetNonSyncingExchanges();
}

const { highlight: highlightExchange, rowClass } = useRowHighlight<{ location: string; name: string }>(
  ({ location, name }) => `${location}#${name}`,
);

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

function addExchange() {
  set(exchange, createNewExchange());
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
    addExchange();
    await router.replace({ query: {} });
  }
  else if (query.location && query.name) {
    const exchangeToEdit = get(rows).find(
      ex => ex.location === query.location && ex.name === query.name,
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
      t('navigation_menu.api_keys'),
      t('navigation_menu.api_keys_sub.exchanges'),
    ]"
  >
    <template #buttons>
      <RuiButton
        color="primary"
        size="lg"
        data-testid="add-exchange"
        @click="addExchange()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('exchange_settings.dialog.add.title') }}
      </RuiButton>
    </template>

    <RuiCard>
      <div class="flex items-center gap-2 mb-2 min-h-8">
        <Transition
          enter-active-class="transition-opacity duration-300"
          enter-from-class="opacity-0"
          leave-active-class="transition-opacity duration-300"
          leave-to-class="opacity-0"
        >
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
              @click="dismissSetupHint()"
            >
              <RuiIcon
                name="lu-x"
                size="14"
              />
            </RuiButton>
          </div>
        </Transition>
        <div class="ml-auto">
          <HintMenuIcon>
            <i18n-t
              scope="global"
              keypath="exchange_settings.subtitle"
              tag="div"
            >
              <ExternalLink
                :text="t('exchange_settings.usage_guide')"
                :url="externalLinks.usageGuideSection.addingAnExchange"
              />
            </i18n-t>
          </HintMenuIcon>
        </div>
      </div>

      <RuiDataTable
        v-model:sort="sort"
        outlined
        row-attr="name"
        data-testid="exchange-table"
        :rows="rows"
        :cols="cols"
        :item-class="rowClass"
      >
        <template #item.location="{ row }">
          <LocationDisplay :identifier="row.location" />
        </template>
        <template #item.syncEnabled="{ row }">
          <RuiSwitch
            color="primary"
            :model-value="!isNonSyncExchange(row)"
            hide-details
            @update:model-value="toggleSync(row)"
          />
        </template>
        <template #item.actions="{ row }">
          <RowActions
            align="center"
            :delete-tooltip="t('exchange_settings.delete.tooltip')"
            :edit-tooltip="t('exchange_settings.edit.tooltip')"
            @delete-click="showRemoveConfirmation(row)"
            @edit-click="editExchange(row)"
          />
        </template>
      </RuiDataTable>
    </RuiCard>

    <ExchangeKeysFormDialog
      v-model="exchange"
      @added="onExchangeAdded($event)"
    />
  </TablePageLayout>
</template>
