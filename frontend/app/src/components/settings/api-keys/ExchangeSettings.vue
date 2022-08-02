<template>
  <div class="exchange-settings" data-cy="exchanges">
    <card outlined-body>
      <template #title>
        {{ $t('exchange_settings.title') }}
      </template>
      <template #subtitle>
        <i18n path="exchange_settings.subtitle" tag="div">
          <base-external-link
            :text="$t('exchange_settings.usage_guide')"
            :href="$interop.usageGuideURL + '#adding-an-exchange'"
          />
        </i18n>
      </template>
      <v-btn
        absolute
        fab
        top
        right
        color="primary"
        data-cy="add-exchange"
        @click="addExchange()"
      >
        <v-icon> mdi-plus </v-icon>
      </v-btn>
      <data-table
        key="index"
        data-cy="exchange-table"
        :items="connectedExchanges"
        :headers="headers"
        sort-by="name"
      >
        <template #item.location="{ item }">
          <location-display :identifier="item.location" />
        </template>
        <template #item.syncEnabled="{ item }">
          <v-switch
            :input-value="!isNonSyncExchange(item)"
            @change="toggleSync(item)"
          />
        </template>
        <template #item.actions="{ item }">
          <row-actions
            :delete-tooltip="$t('exchange_settings.delete.tooltip')"
            :edit-tooltip="$t('exchange_settings.edit.tooltip')"
            @delete-click="confirmRemoval(item)"
            @edit-click="editExchange(item)"
          />
        </template>
      </data-table>
    </card>
    <confirm-dialog
      :display="confirmation"
      :title="$t('exchange_settings.confirmation.title')"
      :message="$t('exchange_settings.confirmation.message', message)"
      @cancel="confirmation = false"
      @confirm="remove()"
    />
    <big-dialog
      :display="showForm"
      :title="
        edit
          ? $tc('exchange_settings.dialog.edit.title')
          : $tc('exchange_settings.dialog.add.title')
      "
      :primary-action="$t('common.actions.save')"
      :secondary-action="$t('common.actions.cancel')"
      :action-disabled="!valid || pending"
      :loading="pending"
      @confirm="setup"
      @cancel="cancel"
    >
      <exchange-keys-form
        v-model="valid"
        :exchange="exchange"
        :edit="edit"
        @update:exchange="exchange = $event"
      />
    </big-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { DataTableHeader } from 'vuetify';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import RowActions from '@/components/helper/RowActions.vue';
import { exchangeName } from '@/components/history/consts';
import ExchangeKeysForm from '@/components/settings/api-keys/ExchangeKeysForm.vue';
import { setupExchanges } from '@/composables/balances';
import { useRouter } from '@/composables/common';
import { useSettings } from '@/composables/settings';
import { default as i18nFn } from '@/i18n';
import { ExchangePayload } from '@/store/balances/types';
import { useNotifications } from '@/store/notifications';
import { Nullable, Writeable } from '@/types';
import { Exchange, SupportedExchange } from '@/types/exchanges';
import { assert } from '@/utils/assertions';

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
const pendingRemoval = ref<Nullable<Exchange>>(null);
const confirmation = ref<boolean>(false);

const { connectedExchanges, setupExchange, removeExchange } = setupExchanges();

const exchange = ref<ExchangePayload>(placeholder());

const showForm = ref<boolean>(false);
const edit = ref<boolean>(false);
const valid = ref<boolean>(false);
const pending = ref<boolean>(false);

const { generalSettings, updateGeneralSetting } = useSettings();

const findNonSyncExchangeIndex = (exchange: Exchange) => {
  return get(nonSyncingExchanges).findIndex((item: Exchange) => {
    return item.name === exchange.name && item.location === exchange.location;
  });
};

const isNonSyncExchange = (exchange: Exchange) => {
  return findNonSyncExchangeIndex(exchange) > -1;
};

const resetNonSyncingExchanges = () => {
  set(nonSyncingExchanges, get(generalSettings).nonSyncingExchanges);
};

const toggleSync = async (exchange: Exchange) => {
  const index = findNonSyncExchangeIndex(exchange);

  let data = [...get(nonSyncingExchanges)];

  let enable = true;

  if (index > -1) {
    enable = false;
    data.splice(index);
  } else {
    data.push({ location: exchange.location, name: exchange.name });
  }

  const status = await updateGeneralSetting({
    nonSyncingExchanges: data
  });

  if ('error' in status) {
    const { notify } = useNotifications();
    notify({
      title: i18nFn.t('exchange_settings.sync.messages.title').toString(),
      message: i18nFn
        .t('exchange_settings.sync.messages.description', {
          action: enable
            ? i18nFn.t('exchange_settings.sync.messages.enable')
            : i18nFn.t('exchange_settings.sync.messages.disable'),
          location: exchange.location,
          name: exchange.name,
          message: status.error
        })
        .toString(),
      display: true
    });
  }

  resetNonSyncingExchanges();
};

const message = computed(() => {
  const exchange = get(pendingRemoval);

  return {
    name: exchange?.name ?? '',
    location: exchange ? exchangeName(exchange.location) : ''
  };
});

const confirmRemoval = (exchangePayload: Exchange) => {
  set(confirmation, true);
  set(pendingRemoval, exchangePayload);
};

const addExchange = () => {
  set(edit, false);
  set(showForm, true);
  set(exchange, placeholder());
};

const editExchange = (exchangePayload: Exchange) => {
  set(edit, true);
  set(showForm, true);
  set(exchange, {
    ...placeholder(),
    ...exchangePayload,
    newName: exchangePayload.name
  });
};

const cancel = () => {
  set(showForm, false);
  set(exchange, placeholder());
};

const setup = async () => {
  set(pending, true);
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

  const success = await setupExchange({
    exchange: writeableExchange,
    edit: get(edit)
  });
  set(pending, false);
  if (success) {
    cancel();
  }
};

const remove = async () => {
  set(confirmation, false);
  const pending = get(pendingRemoval);
  assert(pending !== null);
  set(pendingRemoval, null);
  const success = await removeExchange(pending);

  if (success) {
    set(exchange, placeholder());
  }
};

onBeforeMount(() => {
  resetNonSyncingExchanges();
});

const router = useRouter();
onMounted(() => {
  const { currentRoute } = router;
  if (currentRoute.query.add) {
    addExchange();
    router.replace({ query: {} });
  }
});

const headers: DataTableHeader[] = [
  {
    text: i18nFn.t('common.location').toString(),
    value: 'location',
    width: '120px',
    align: 'center'
  },
  {
    text: i18nFn.t('common.name').toString(),
    value: 'name'
  },
  {
    text: i18nFn.t('exchange_settings.header.sync_enabled').toString(),
    value: 'syncEnabled'
  },
  {
    text: i18nFn.t('exchange_settings.header.actions').toString(),
    value: 'actions',
    width: '105px',
    align: 'center',
    sortable: false
  }
];
</script>

<style scoped lang="scss">
.exchange-settings {
  &__connected-exchanges {
    display: flex;
    flex-direction: row;
    justify-content: flex-start;
    padding: 8px;
  }

  &__fields {
    &__exchange {
      ::v-deep {
        .v-select {
          &__selections {
            height: 36px;
          }
        }
      }
    }
  }
}
</style>
