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
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      :primary-action="$t('exchange_settings.button.save')"
      :secondary-action="$t('exchange_settings.button.cancel')"
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

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapState } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import ExchangeDisplay from '@/components/display/ExchangeDisplay.vue';
import RowActions from '@/components/helper/RowActions.vue';
import { exchangeName } from '@/components/history/consts';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import ExchangeKeysForm from '@/components/settings/api-keys/ExchangeKeysForm.vue';
import SettingsMixin from '@/mixins/settings-mixin';
import { ExchangePayload, ExchangeSetupPayload } from '@/store/balances/types';
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

@Component({
  components: {
    BigDialog,
    ExchangeKeysForm,
    RowActions,
    ExchangeDisplay,
    RevealableInput,
    ConfirmDialog,
    BaseExternalLink
  },
  computed: {
    ...mapState('balances', ['connectedExchanges'])
  },
  methods: {
    ...mapActions('balances', ['setupExchange', 'removeExchange'])
  }
})
export default class ExchangeSettings extends Mixins(SettingsMixin) {
  nonSyncingExchanges: Exchange[] = [];
  pendingRemoval: Nullable<Exchange> = null;
  confirmation: boolean = false;
  setupExchange!: (payload: ExchangeSetupPayload) => Promise<boolean>;
  removeExchange!: (exchange: Exchange) => Promise<boolean>;

  exchange: ExchangePayload = placeholder();

  showForm: boolean = false;
  edit: boolean = false;
  valid: boolean = false;
  pending: boolean = false;
  binancePairs: string[] = [];

  created() {
    this.nonSyncingExchanges = this.generalSettings.nonSyncingExchanges;
  }

  mounted() {
    const { currentRoute } = this.$router;
    if (currentRoute.query.add) {
      this.addExchange();
      this.$router.replace({ query: {} });
    }
  }

  findNonSyncExchangeIndex(exchange: Exchange) {
    return this.nonSyncingExchanges.findIndex((item: Exchange) => {
      return item.name === exchange.name && item.location === exchange.location;
    });
  }

  isNonSyncExchange(exchange: Exchange) {
    return this.findNonSyncExchangeIndex(exchange) > -1;
  }

  async toggleSync(exchange: Exchange) {
    const index = this.findNonSyncExchangeIndex(exchange);

    let data = [...this.nonSyncingExchanges];

    let enable = true;

    if (index > -1) {
      enable = false;
      data.splice(index);
    } else {
      data.push({ location: exchange.location, name: exchange.name });
    }

    const status = await this.settingsUpdate({
      nonSyncingExchanges: data
    });

    if (!status.success) {
      const { notify } = useNotifications();
      notify({
        title: this.$t('exchange_settings.sync.messages.title').toString(),
        message: this.$t('exchange_settings.sync.messages.description', {
          action: enable
            ? this.$t('exchange_settings.sync.messages.enable')
            : this.$t('exchange_settings.sync.messages.disable'),
          location: exchange.location,
          name: exchange.name,
          message: status.message
        }).toString(),
        display: true
      });
    }

    this.nonSyncingExchanges = this.generalSettings.nonSyncingExchanges;
  }

  get dialogTitle(): string {
    return this.edit
      ? this.$t('exchange_settings.dialog.edit.title').toString()
      : this.$t('exchange_settings.dialog.add.title').toString();
  }

  get dialogSubtitle(): string {
    return '';
  }

  get message() {
    const exchange = this.pendingRemoval;

    return {
      name: exchange?.name ?? '',
      location: exchange ? exchangeName(exchange.location) : ''
    };
  }

  readonly headers: DataTableHeader[] = [
    {
      text: this.$t('exchange_settings.header.location').toString(),
      value: 'location',
      width: '120px',
      align: 'center'
    },
    {
      text: this.$t('exchange_settings.header.name').toString(),
      value: 'name'
    },
    {
      text: this.$t('exchange_settings.header.sync_enabled').toString(),
      value: 'syncEnabled'
    },
    {
      text: this.$t('exchange_settings.header.actions').toString(),
      value: 'actions',
      width: '105px',
      align: 'center',
      sortable: false
    }
  ];

  confirmRemoval(exchange: Exchange) {
    this.confirmation = true;
    this.pendingRemoval = exchange;
  }

  addExchange() {
    this.edit = false;
    this.showForm = true;
    this.exchange = placeholder();
  }

  editExchange(exchange: Exchange) {
    this.edit = true;
    this.showForm = true;
    this.exchange = { ...placeholder(), ...exchange, newName: exchange.name };
  }

  cancel() {
    this.showForm = false;
    this.exchange = placeholder();
  }

  async setup() {
    this.pending = true;
    const exchange: Writeable<ExchangePayload> = { ...this.exchange };
    if (exchange.name === exchange.newName) {
      exchange.newName = null;
    }

    if (
      !!exchange.ftxSubaccount &&
      exchange.ftxSubaccount.trim().length === 0
    ) {
      exchange.ftxSubaccount = null;
    }

    const success = await this.setupExchange({
      exchange: exchange,
      edit: this.edit
    });
    this.pending = false;
    if (success) {
      this.cancel();
    }
  }

  async remove() {
    this.confirmation = false;
    const exchange = this.pendingRemoval;
    assert(exchange !== null);
    this.pendingRemoval = null;
    const success = await this.removeExchange(exchange);

    if (success) {
      this.exchange = placeholder();
    }
  }
}
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
