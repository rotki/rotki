<template>
  <v-form
    :value="value"
    data-cy="ledger-action-form"
    class="ledger-action-form"
    @input="input"
  >
    <location-selector
      v-model="location"
      class="pt-1"
      required
      outlined
      data-cy="location"
      :rules="locationRules"
      :label="$t('ledger_action_form.location.label')"
      :error-messages="errorMessages['location']"
      @focus="delete errorMessages['location']"
    />

    <date-time-picker
      v-model="datetime"
      outlined
      :label="$t('ledger_action_form.date.label')"
      persistent-hint
      required
      seconds
      limit-now
      data-cy="datetime"
      :hint="$t('ledger_action_form.date.hint')"
      :error-messages="errorMessages['timestamp']"
      @focus="delete errorMessages['timestamp']"
    />

    <v-row
      align="center"
      :class="
        $vuetify.breakpoint.mdAndUp
          ? 'ledger-action-form__amount-wrapper'
          : null
      "
    >
      <v-col cols="12" md="4">
        <asset-select
          v-model="asset"
          outlined
          required
          data-cy="asset"
          :rules="assetRules"
          :error-messages="errorMessages['asset']"
          @focus="delete errorMessages['asset']"
        />
      </v-col>

      <v-col cols="12" md="4">
        <amount-input
          v-model="amount"
          outlined
          :rules="amountRules"
          required
          data-cy="amount"
          :label="$t('ledger_action_form.amount.label')"
          :error-messages="errorMessages['amount']"
          @focus="delete errorMessages['amount']"
        />
      </v-col>

      <v-col cols="12" md="4">
        <v-select
          v-model="actionType"
          outlined
          :label="$t('ledger_action_form.type.label')"
          :items="typeData"
          item-value="identifier"
          item-text="label"
          required
          data-cy="action-type"
          :error-messages="errorMessages['actionType']"
          @focus="delete errorMessages['actionType']"
        />
      </v-col>
    </v-row>

    <v-divider class="mb-6 mt-2" />

    <v-row
      :class="
        $vuetify.breakpoint.mdAndUp ? 'ledger-action-form__rate-wrapper' : null
      "
    >
      <v-col cols="12" md="8">
        <amount-input
          v-model="rate"
          outlined
          persistent-hint
          data-cy="rate"
          :hint="$t('ledger_action_form.rate.hint')"
          :label="$t('ledger_action_form.rate.label')"
          :error-messages="errorMessages['rate']"
          @focus="delete errorMessages['rate']"
        />
      </v-col>
      <v-col cols="12" md="4">
        <asset-select
          v-model="rateAsset"
          outlined
          :label="$t('ledger_action_form.rate_asset.label')"
          :hint="$t('ledger_action_form.rate_asset.hint')"
          persistent-hint
          data-cy="rate-asset"
          :error-messages="errorMessages['rateAsset']"
          @focus="delete errorMessages['rateAsset']"
        />
      </v-col>
    </v-row>

    <v-text-field
      v-model="link"
      outlined
      prepend-inner-icon="mdi-link"
      persistent-hint
      data-cy="link"
      :label="$t('ledger_action_form.link.label')"
      :hint="$t('ledger_action_form.link.hint')"
      :error-messages="errorMessages['link']"
      @focus="delete errorMessages['link']"
    />

    <v-textarea
      v-model="notes"
      prepend-inner-icon="mdi-text-box-outline"
      persistent-hint
      outlined
      data-cy="notes"
      :label="$t('ledger_action_form.notes.label')"
      :hint="$t('ledger_action_form.notes.hint')"
      :error-messages="errorMessages['notes']"
      @focus="delete errorMessages['notes']"
    />
  </v-form>
</template>

<script lang="ts">
import dayjs from 'dayjs';
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { convertKeys } from '@/services/axios-tranformers';
import { deserializeApiErrorMessage } from '@/services/converters';
import {
  LedgerAction,
  NewLedgerAction,
  TradeLocation
} from '@/services/history/types';
import { HistoryActions, ledgerActionsData } from '@/store/history/consts';
import { ActionStatus } from '@/store/types';
import { Writeable } from '@/types';
import { LedgerActionType } from '@/types/ledger-actions';
import { bigNumberify, Zero } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';

const LAST_LOCATION = 'rotki.ledger_action.location';

function setLastSelectedLocation(location: TradeLocation) {
  localStorage.setItem(LAST_LOCATION, location);
}

function lastSelectedLocation(): TradeLocation {
  const item = localStorage.getItem(LAST_LOCATION);
  if (item) {
    return item as TradeLocation;
  }
  return TRADE_LOCATION_EXTERNAL;
}

@Component({
  components: { LocationSelector },
  methods: {
    ...mapActions('history', [
      HistoryActions.ADD_LEDGER_ACTION,
      HistoryActions.EDIT_LEDGER_ACTION
    ])
  }
})
export default class LedgerActionForm extends Vue {
  @Prop({ required: false, type: Boolean, default: false })
  value!: boolean;

  @Prop({ required: false, default: null })
  edit!: LedgerAction | null;

  @Emit()
  input(_valid: boolean) {}

  @Emit()
  refresh() {}

  errorMessages: {
    [field: string]: string[];
  } = {};
  addLedgerAction!: (ledgerAction: NewLedgerAction) => Promise<ActionStatus>;
  editLedgerAction!: (
    ledgerAction: Omit<LedgerAction, 'ignoredInAccounting'>
  ) => Promise<ActionStatus>;

  readonly typeData = ledgerActionsData;
  readonly amountRules = [
    (v: string) =>
      !!v ||
      this.$t('ledger_action_form.amount.validation.non_empty').toString()
  ];
  readonly assetRules = [
    (v: string) =>
      !!v || this.$t('ledger_action_form.asset.validation.non_empty').toString()
  ];

  readonly locationRules = [
    (v: string) =>
      !!v ||
      this.$t('ledger_action_form.location.validation.non_empty').toString()
  ];

  id: number | null = null;
  location: string = '';
  datetime: string = '';
  asset: string = '';
  amount: string = '';
  actionType: string = '';
  rate: string = '';
  rateAsset: string = '';
  link: string = '';
  notes: string = '';

  mounted() {
    this.setEditMode();
  }

  @Watch('edit')
  onEdit() {
    this.setEditMode();
  }

  private setEditMode() {
    if (!this.edit) {
      this.reset();
      return;
    }

    const ledgerAction: LedgerAction = this.edit;

    this.location = ledgerAction.location;
    this.datetime = convertFromTimestamp(ledgerAction.timestamp, true);
    this.asset = ledgerAction.asset;
    this.amount = ledgerAction.amount.toString();
    this.actionType = ledgerAction.actionType.toString();
    this.rate = ledgerAction.rate?.toString() ?? '';
    this.rateAsset = ledgerAction.rateAsset ?? '';
    this.link = ledgerAction.link ?? '';
    this.notes = ledgerAction.notes ?? '';
    this.id = ledgerAction.identifier;
  }

  @Watch('location')
  onLocationUpdate(location: string) {
    if (location) {
      setLastSelectedLocation(location);
    }
  }

  reset() {
    this.id = null;
    this.location = lastSelectedLocation();
    this.datetime = convertFromTimestamp(dayjs().unix(), true);
    this.asset = '';
    this.amount = '0';
    this.actionType = LedgerActionType.ACTION_INCOME;
    this.rate = '';
    this.rateAsset = '';
    this.link = '';
    this.notes = '';
    this.errorMessages = {};
  }

  async save(): Promise<boolean> {
    const amount = bigNumberify(this.amount);
    const rate = bigNumberify(this.rate);

    const ledgerActionPayload: Writeable<NewLedgerAction> = {
      location: this.location,
      timestamp: convertToTimestamp(this.datetime),
      asset: this.asset,
      amount: amount.isNaN() ? Zero : amount,
      actionType: this.actionType as LedgerActionType,
      rate: rate.isNaN() || rate.isZero() ? undefined : rate,
      rateAsset: this.rateAsset ? this.rateAsset : undefined,
      link: this.link ? this.link : undefined,
      notes: this.notes ? this.notes : undefined
    };

    const { success, message } = !this.id
      ? await this.addLedgerAction(ledgerActionPayload)
      : await this.editLedgerAction({
          ...ledgerActionPayload,
          identifier: this.id
        });

    if (success) {
      this.refresh();
      this.reset();
      return true;
    }
    if (message) {
      this.errorMessages = convertKeys(
        deserializeApiErrorMessage(message) ?? {},
        true,
        false
      );
    }

    return false;
  }
}
</script>

<style scoped lang="scss">
.ledger-action-form {
  &__amount-wrapper,
  &__rate-wrapper {
    ::v-deep {
      .v-input {
        input {
          height: 60px;
          max-height: 60px !important;
        }
      }
    }
  }

  ::v-deep {
    /* stylelint-disable selector-class-pattern,selector-nested-pattern,scss/selector-nest-combinators,rule-empty-line-before */
    .v-select.v-text-field--outlined:not(.v-text-field--single-line) {
      .v-select__selections {
        padding: 0 !important;
      }
    }

    /* stylelint-enable selector-class-pattern,selector-nested-pattern,scss/selector-nest-combinators,rule-empty-line-before */
  }
}
</style>
