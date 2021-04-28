<template>
  <v-form :value="value" class="ledger-action-form" @input="input">
    <location-selector
      class="pt-1"
      required
      outlined
      :error-messages="errors['location']"
      :value="action.location"
      :rules="locationRules"
      :label="$t('ledger_action_form.location.label')"
      @input="updateAction('location', $event)"
    />

    <date-time-picker
      outlined
      :error-messages="errors['timestamp']"
      :value="action.timestamp > 0 ? convertFromTs(action.timestamp) : ''"
      :label="$t('ledger_action_form.date.label')"
      persistent-hint
      required
      seconds
      :hint="$t('ledger_action_form.date.hint')"
      @input="onDateChange($event)"
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
          outlined
          :error-messages="errors['asset']"
          :value="action.asset"
          required
          :rules="assetRules"
          @input="updateAction('asset', $event)"
        />
      </v-col>

      <v-col cols="12" md="4">
        <v-text-field
          outlined
          :error-messages="errors['amount']"
          :value="action.amount"
          :rules="amountRules"
          type="number"
          required
          :label="$t('ledger_action_form.amount.label')"
          @input="updateAction('amount', $event)"
        />
      </v-col>

      <v-col cols="12" md="4">
        <v-select
          outlined
          :error-messages="errors['actionType']"
          :value="action.actionType"
          :label="$t('ledger_action_form.type.label')"
          :items="typeData"
          item-value="identifier"
          item-text="label"
          required
          @input="updateAction('actionType', $event)"
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
        <v-text-field
          outlined
          type="number"
          persistent-hint
          :error-messages="errors['rate']"
          :value="action.rate"
          :hint="$t('ledger_action_form.rate.hint')"
          :label="$t('ledger_action_form.rate.label')"
          @input="updateAction('rate', $event)"
        />
      </v-col>
      <v-col cols="12" md="4">
        <asset-select
          outlined
          :error-messages="errors['rateAsset']"
          :value="action.rateAsset"
          :label="$t('ledger_action_form.rate_asset.label')"
          :hint="$t('ledger_action_form.rate_asset.hint')"
          persistent-hint
          @input="updateAction('rateAsset', $event)"
        />
      </v-col>
    </v-row>

    <v-text-field
      outlined
      :error-messages="errors['link']"
      prepend-inner-icon="mdi-link"
      persistent-hint
      :value="action.link"
      :label="$t('ledger_action_form.link.label')"
      :hint="$t('ledger_action_form.link.hint')"
      @input="updateAction('link', $event)"
    />

    <v-textarea
      prepend-inner-icon="mdi-text-box-outline"
      :error-messages="errors['notes']"
      persistent-hint
      :value="action.notes"
      outlined
      :label="$t('ledger_action_form.notes.label')"
      :hint="$t('ledger_action_form.notes.hint')"
      @input="updateAction('notes', $event)"
    />
  </v-form>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import { ledgerActionsData } from '@/store/history/consts';
import { LedgerAction, UnsavedAction } from '@/store/history/types';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';

type Action = LedgerAction | UnsavedAction;

@Component({
  components: { LocationSelector }
})
export default class LedgerActionForm extends Vue {
  @Prop({ required: false, type: Boolean, default: false })
  value!: boolean;
  @Prop({ required: true, type: Object })
  action!: Action;
  @Prop({ required: true, type: Object })
  errors!: { [key in keyof UnsavedAction]?: string };

  @Emit()
  input(_value: boolean) {}

  @Emit('action:update')
  actionUpdate(_action: Action) {}

  onDateChange(date: string) {
    if (!date) {
      return;
    }
    this.actionUpdate({ ...this.action, timestamp: convertToTimestamp(date) });
  }

  updateAction(prop: keyof UnsavedAction, value: string | null) {
    this.actionUpdate({ ...this.action, [prop]: value });
  }

  convertFromTs(timestamp: number) {
    return convertFromTimestamp(timestamp, true);
  }

  datetime = '';

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
