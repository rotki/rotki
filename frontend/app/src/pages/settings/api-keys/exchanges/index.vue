<script setup lang="ts">
import {
  type DataTableColumn,
  type DataTableSortColumn
} from '@rotki/ui-library-compat';
import { type Writeable } from '@/types';
import {
  type Exchange,
  type ExchangePayload,
  SupportedExchange
} from '@/types/exchanges';

const placeholder: () => ExchangePayload = () => ({
  location: SupportedExchange.KRAKEN,
  name: '',
  newName: null,
  apiKey: null,
  apiSecret: null,
  passphrase: null,
  krakenAccountType: 'starter',
  binanceMarkets: null,
  ftxSubaccount: null
});

const nonSyncingExchanges = ref<Exchange[]>([]);

const store = useExchangesStore();
const { setupExchange, removeExchange } = store;
const { connectedExchanges } = storeToRefs(store);

const exchange = ref<ExchangePayload>(placeholder());
const editMode = ref<boolean>(false);
const sort = ref<DataTableSortColumn>({
  column: 'name',
  direction: 'asc'
});

const { nonSyncingExchanges: current } = storeToRefs(useGeneralSettingsStore());
const { update } = useSettingsStore();

const { t } = useI18n();
const { usageGuideUrl } = useInterop();

const findNonSyncExchangeIndex = (exchange: Exchange) =>
  get(nonSyncingExchanges).findIndex(
    (item: Exchange) =>
      item.name === exchange.name && item.location === exchange.location
  );

const isNonSyncExchange = (exchange: Exchange) =>
  findNonSyncExchangeIndex(exchange) > -1;

const resetNonSyncingExchanges = () => {
  set(nonSyncingExchanges, get(current));
};

const toggleSync = async (exchange: Exchange) => {
  const index = findNonSyncExchangeIndex(exchange);

  const data = [...get(nonSyncingExchanges)];

  let enable = true;

  if (index > -1) {
    enable = false;
    data.splice(index);
  } else {
    data.push({ location: exchange.location, name: exchange.name });
  }

  const status = await update({
    nonSyncingExchanges: data
  });

  if (!status.success) {
    const { notify } = useNotificationsStore();
    notify({
      title: t('exchange_settings.sync.messages.title'),
      message: t('exchange_settings.sync.messages.description', {
        action: enable
          ? t('exchange_settings.sync.messages.enable')
          : t('exchange_settings.sync.messages.disable'),
        location: exchange.location,
        name: exchange.name,
        message: status.message
      }),
      display: true
    });
  }

  resetNonSyncingExchanges();
};

const { exchangeName } = useLocations();

const { setOpenDialog, closeDialog, setSubmitFunc, setPostSubmitFunc } =
  useExchangeApiKeysForm();

const addExchange = () => {
  set(editMode, false);
  setOpenDialog(true);
  set(exchange, placeholder());
};

const editExchange = (exchangePayload: Exchange) => {
  set(editMode, true);
  setOpenDialog(true);
  set(exchange, {
    ...placeholder(),
    ...exchangePayload,
    newName: exchangePayload.name
  });
};

const resetForm = () => {
  closeDialog();
  set(exchange, placeholder());
};

setPostSubmitFunc(resetForm);

const setup = async (): Promise<boolean> => {
  const writeableExchange: Writeable<ExchangePayload> = { ...get(exchange) };
  if (writeableExchange.name === writeableExchange.newName) {
    writeableExchange.newName = null;
  }

  if (
    !!writeableExchange.ftxSubaccount &&
    writeableExchange.ftxSubaccount.trim().length === 0
  ) {
    writeableExchange.ftxSubaccount = null;
  }

  return await setupExchange({
    exchange: writeableExchange,
    edit: get(editMode)
  });
};

setSubmitFunc(setup);

const remove = async (item: Exchange) => {
  const success = await removeExchange(item);

  if (success) {
    set(exchange, placeholder());
  }
};

onBeforeMount(() => {
  resetNonSyncingExchanges();
});

const router = useRouter();
onMounted(async () => {
  const { currentRoute } = router;
  if (currentRoute.query.add) {
    addExchange();
    await router.replace({ query: {} });
  }
});

const headers = computed<DataTableColumn[]>(() => [
  {
    label: t('common.location'),
    key: 'location',
    width: '120px',
    align: 'center'
  },
  {
    label: t('common.name'),
    key: 'name'
  },
  {
    label: t('exchange_settings.header.sync_enabled'),
    key: 'syncEnabled'
  },
  {
    label: t('common.actions_text'),
    key: 'actions',
    width: '105px',
    align: 'center'
  }
]);

const { show } = useConfirmStore();

const showRemoveConfirmation = (item: Exchange) => {
  show(
    {
      title: t('exchange_settings.confirmation.title'),
      message: t('exchange_settings.confirmation.message', {
        name: item?.name ?? '',
        location: item ? exchangeName(item.location) : ''
      })
    },
    () => remove(item)
  );
};
</script>

<template>
  <TablePageLayout
    class="exchange-settings"
    data-cy="exchanges"
    :title="[
      t('navigation_menu.api_keys'),
      t('navigation_menu.api_keys_sub.exchanges')
    ]"
  >
    <template #buttons>
      <RuiButton color="primary" data-cy="add-exchange" @click="addExchange()">
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('exchange_settings.dialog.add.title') }}
      </RuiButton>
    </template>

    <RuiCard>
      <div class="flex flex-row-reverse">
        <HintMenuIcon>
          <i18n path="exchange_settings.subtitle" tag="div">
            <BaseExternalLink
              :text="t('exchange_settings.usage_guide')"
              :href="usageGuideUrl + '#adding-an-exchange'"
            />
          </i18n>
        </HintMenuIcon>
      </div>

      <RuiDataTable
        outlined
        data-cy="exchange-table"
        :rows="connectedExchanges"
        :cols="headers"
        :sort="sort"
      >
        <template #item.location="{ row }">
          <LocationDisplay :identifier="row.location" />
        </template>
        <template #item.syncEnabled="{ row }">
          <VSwitch
            :input-value="!isNonSyncExchange(row)"
            @change="toggleSync(row)"
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
