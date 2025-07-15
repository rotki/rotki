<script setup lang="ts">
import type { DataTableColumn, DataTableSortColumn } from '@rotki/ui-library';
import type { Exchange, ExchangeFormData } from '@/types/exchanges';
import { externalLinks } from '@shared/external-links';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import RowActions from '@/components/helper/RowActions.vue';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import ExchangeKeysFormDialog from '@/components/settings/api-keys/exchange/ExchangeKeysFormDialog.vue';
import { useLocations } from '@/composables/locations';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useConfirmStore } from '@/store/confirm';
import { useLocationStore } from '@/store/locations';
import { useNotificationsStore } from '@/store/notifications';
import { useSettingsStore } from '@/store/settings';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';

const nonSyncingExchanges = ref<Exchange[]>([]);
const exchange = ref<ExchangeFormData>();
const sort = ref<DataTableSortColumn<Exchange>>({
  column: 'name',
  direction: 'asc',
});

const { exchangesWithKey } = storeToRefs(useLocationStore());
const { removeExchange } = useExchanges();
const { connectedExchanges: rows } = storeToRefs(useSessionSettingsStore());
const { nonSyncingExchanges: current } = storeToRefs(useGeneralSettingsStore());
const { update } = useSettingsStore();
const { show } = useConfirmStore();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute('/api-keys/exchanges/');
const { exchangeName } = useLocations();

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
    binanceMarkets: undefined,
    krakenAccountType: 'starter',
    location: get(exchangesWithKey)[0],
    mode: 'add',
    name: '',
    newName: '',
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
    const { notify } = useNotificationsStore();
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
      location: item ? exchangeName(item.location) : '',
      name: item?.name ?? '',
    }),
    title: t('exchange_settings.confirmation.title'),
  }, () => remove(item));
}

onBeforeMount(() => {
  resetNonSyncingExchanges();
});

onMounted(async () => {
  const { query } = get(route);
  if (query.add) {
    addExchange();
    await router.replace({ query: {} });
  }
});
</script>

<template>
  <TablePageLayout
    class="exchange-settings"
    data-cy="exchanges"
    :title="[
      t('navigation_menu.api_keys'),
      t('navigation_menu.api_keys_sub.exchanges'),
    ]"
  >
    <template #buttons>
      <RuiButton
        color="primary"
        data-cy="add-exchange"
        @click="addExchange()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('exchange_settings.dialog.add.title') }}
      </RuiButton>
    </template>

    <RuiCard>
      <div class="flex flex-row-reverse mb-2">
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

      <RuiDataTable
        v-model:sort="sort"
        outlined
        row-attr="name"
        data-cy="exchange-table"
        :rows="rows"
        :cols="cols"
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

    <ExchangeKeysFormDialog v-model="exchange" />
  </TablePageLayout>
</template>
