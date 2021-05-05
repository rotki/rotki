<template>
  <v-container class="exchange-settings">
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
      <v-btn absolute fab top right color="primary" @click="addExchange()">
        <v-icon> mdi-plus </v-icon>
      </v-btn>
      <data-table
        key="index"
        :items="connectedExchanges"
        :headers="headers"
        sort-by="name"
      >
        <template #item.location="{ item }">
          <location-display :identifier="item.location" />
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
      :message="
        $t('exchange_settings.confirmation.message', {
          exchange: pendingRemoval
        })
      "
      @cancel="confirmation = false"
      @confirm="remove()"
    />
    <big-dialog
      :display="showForm"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      :primary-action="$t('exchange_settings.button.save')"
      :secondary-action="$t('exchange_settings.button.cancel')"
      :action-disabled="!valid"
      @confirm="setup"
      @cancel="cancel"
    >
      <exchange-keys-form
        v-model="valid"
        :exchange="exchange"
        @update:exchange="exchange = $event"
      />
    </big-dialog>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapState } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import ExchangeDisplay from '@/components/display/ExchangeDisplay.vue';
import ExchangeBadge from '@/components/ExchangeBadge.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import ExchangeKeysForm from '@/components/settings/api-keys/ExchangeKeysForm.vue';
import { SUPPORTED_EXCHANGES } from '@/data/defaults';
import { Exchange } from '@/model/action-result';
import { ExchangePayload } from '@/store/balances/types';
import { Nullable } from '@/types';
import { assert } from '@/utils/assertions';

const placeholder: () => Exchange = () => ({
  location: SUPPORTED_EXCHANGES[0],
  name: ''
});

@Component({
  components: {
    BigDialog,
    ExchangeKeysForm,
    RowActions,
    ExchangeDisplay,
    RevealableInput,
    ConfirmDialog,
    ExchangeBadge,
    BaseExternalLink
  },
  computed: {
    ...mapState('balances', ['connectedExchanges'])
  },
  methods: {
    ...mapActions('balances', ['setupExchange', 'removeExchange'])
  }
})
export default class ExchangeSettings extends Vue {
  pendingRemoval: Nullable<Exchange> = null;
  confirmation: boolean = false;

  connectedExchanges!: string[];
  setupExchange!: (payload: ExchangePayload) => Promise<boolean>;
  removeExchange!: (exchange: Exchange) => Promise<boolean>;

  exchange: Exchange = placeholder();

  showForm: boolean = false;
  valid: boolean = false;

  get dialogTitle(): string {
    return '';
  }

  get dialogSubtitle(): string {
    return '';
  }

  readonly headers: DataTableHeader[] = [
    {
      text: 'Location',
      value: 'location',
      width: '120px',
      align: 'center'
    },
    {
      text: 'Name',
      value: 'name'
    },
    {
      text: 'Actions',
      value: 'actions',
      width: '105px',
      align: 'center',
      sortable: false
    }
  ];

  get isConnected(): boolean {
    return (
      this.connectedExchanges.findIndex(
        value => value === this.selectedExchange
      ) >= 0
    );
  }

  confirmRemoval(exchange: Exchange) {
    this.confirmation = true;
    this.pendingRemoval = exchange;
  }

  editExchange(exchange: Exchange) {
    this.showForm = true;
    this.exchange = exchange;
  }

  cancel() {
    this.showForm = false;
    this.exchange = placeholder();
  }

  async setup() {
    await this.setupExchange(this.exchange);
  }

  async remove() {
    this.confirmation = false;
    const exchange = this.pendingRemoval;
    assert(exchange !== null);
    this.pendingRemoval = null;
    const success = await this.removeExchange(exchange);
    if (success) {
      this.resetFields(true);
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

  ::v-deep {
    .v-input {
      &--is-disabled {
        .v-icon,
        .v-label {
          color: green !important;
        }
      }
    }
  }
}
</style>
