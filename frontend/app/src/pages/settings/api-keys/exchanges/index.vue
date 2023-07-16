<script setup lang="ts">
import { type DataTableHeader } from '@/types/vuetify';
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

const headers: DataTableHeader[] = [
  {
    text: t('common.location'),
    value: 'location',
    width: '120px',
    align: 'center'
  },
  {
    text: t('common.name'),
    value: 'name'
  },
  {
    text: t('exchange_settings.header.sync_enabled'),
    value: 'syncEnabled'
  },
  {
    text: t('exchange_settings.header.actions'),
    value: 'actions',
    width: '105px',
    align: 'center',
    sortable: false
  }
];

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
  <div class="exchange-settings" data-cy="exchanges">
    <Card outlined-body>
      <template #title>
        {{ t('exchange_settings.title') }}
      </template>
      <template #subtitle>
        <I18n path="exchange_settings.subtitle" tag="div">
          <BaseExternalLink
            :text="t('exchange_settings.usage_guide')"
            :href="usageGuideUrl + '#adding-an-exchange'"
          />
        </I18n>
      </template>
      <VBtn
        absolute
        fab
        top
        right
        color="primary"
        data-cy="add-exchange"
        @click="addExchange()"
      >
        <VIcon> mdi-plus </VIcon>
      </VBtn>
      <DataTable
        key="index"
        data-cy="exchange-table"
        :items="connectedExchanges"
        :headers="headers"
        sort-by="name"
      >
        <template #item.location="{ item }">
          <LocationDisplay :identifier="item.location" />
        </template>
        <template #item.syncEnabled="{ item }">
          <VSwitch
            :input-value="!isNonSyncExchange(item)"
            @change="toggleSync(item)"
          />
        </template>
        <template #item.actions="{ item }">
          <RowActions
            :delete-tooltip="t('exchange_settings.delete.tooltip')"
            :edit-tooltip="t('exchange_settings.edit.tooltip')"
            @delete-click="showRemoveConfirmation(item)"
            @edit-click="editExchange(item)"
          />
        </template>
      </DataTable>
    </Card>

    <ExchangeKeysFormDialog
      v-model="exchange"
      :edit-mode="editMode"
      @reset="resetForm()"
    />
  </div>
</template>
