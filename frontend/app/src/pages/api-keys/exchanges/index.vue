<script setup lang="ts">
import type { DataTableColumn, DataTableSortColumn } from '@rotki/ui-library';
import type { Writeable } from '@rotki/common';
import type { Exchange, ExchangePayload } from '@/types/exchanges';

const { exchangesWithKey } = storeToRefs(useLocationStore());

const placeholder: () => ExchangePayload = () => ({
  location: get(exchangesWithKey)[0],
  name: '',
  newName: null,
  apiKey: null,
  apiSecret: null,
  passphrase: null,
  krakenAccountType: 'starter',
  binanceMarkets: null,
});

const nonSyncingExchanges = ref<Exchange[]>([]);
const exchange = ref<ExchangePayload>(placeholder());
const editMode = ref<boolean>(false);
const sort = ref<DataTableSortColumn<Exchange>>({
  column: 'name',
  direction: 'asc',
});

const store = useExchangesStore();
const { setupExchange, removeExchange } = store;
const { connectedExchanges: rows } = storeToRefs(store);

const { nonSyncingExchanges: current } = storeToRefs(useGeneralSettingsStore());
const { update } = useSettingsStore();

const { t } = useI18n();

const cols = computed<DataTableColumn<Exchange>[]>(() => [
  {
    label: t('common.location'),
    key: 'location',
    width: '120px',
    align: 'center',
    cellClass: 'py-0',
  },
  {
    label: t('common.name'),
    key: 'name',
  },
  {
    label: t('exchange_settings.header.sync_enabled'),
    key: 'syncEnabled',
  },
  {
    label: t('common.actions_text'),
    key: 'actions',
    width: '105px',
    align: 'center',
  },
]);

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
      title: t('exchange_settings.sync.messages.title'),
      message: t('exchange_settings.sync.messages.description', {
        action: enable ? t('exchange_settings.sync.messages.enable') : t('exchange_settings.sync.messages.disable'),
        location: exchange.location,
        name: exchange.name,
        message: status.message,
      }),
      display: true,
    });
  }

  resetNonSyncingExchanges();
}

const { exchangeName } = useLocations();

const { setOpenDialog, closeDialog, setSubmitFunc, setPostSubmitFunc } = useExchangeApiKeysForm();

function addExchange() {
  set(editMode, false);
  setOpenDialog(true);
  set(exchange, placeholder());
}

function editExchange(exchangePayload: Exchange) {
  set(editMode, true);
  setOpenDialog(true);
  set(exchange, {
    ...placeholder(),
    ...exchangePayload,
    newName: exchangePayload.name,
  });
}

function resetForm() {
  closeDialog();
  set(exchange, placeholder());
}

setPostSubmitFunc(resetForm);

async function setup(): Promise<boolean> {
  const writeableExchange: Writeable<ExchangePayload> = { ...get(exchange) };
  if (writeableExchange.name === writeableExchange.newName)
    writeableExchange.newName = null;

  return await setupExchange({
    exchange: writeableExchange,
    edit: get(editMode),
  });
}

setSubmitFunc(setup);

async function remove(item: Exchange) {
  const success = await removeExchange(item);

  if (success)
    set(exchange, placeholder());
}

const router = useRouter();
const route = useRoute('/api-keys/exchanges/');

const { show } = useConfirmStore();

function showRemoveConfirmation(item: Exchange) {
  show({
    title: t('exchange_settings.confirmation.title'),
    message: t('exchange_settings.confirmation.message', {
      name: item?.name ?? '',
      location: item ? exchangeName(item.location) : '',
    }),
  }, () => remove(item));
}

onBeforeMount(() => {
  resetNonSyncingExchanges();
});

onMounted(async () => {
  const { query } = get(route);
  if (query.add) {
    await router.replace({ query: {} });
    startPromise(nextTick(() => addExchange()));
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
          <RuiIcon name="add-line" />
        </template>
        {{ t('exchange_settings.dialog.add.title') }}
      </RuiButton>
    </template>

    <RuiCard>
      <div class="flex flex-row-reverse mb-2">
        <HintMenuIcon>
          <i18n-t
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
        outlined
        row-attr="name"
        data-cy="exchange-table"
        :rows="rows"
        :cols="cols"
        :sort="sort"
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
      :edit-mode="editMode"
      @reset="resetForm()"
    />
  </TablePageLayout>
</template>
