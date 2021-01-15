<template>
  <v-form :value="value" @input="input">
    <location-selector
      :error-messages="errors['location']"
      :value="action.location"
      :rules="locationRules"
      :label="$t('ledger_action_form.location.label')"
      @input="updateAction('location', $event)"
    />

    <date-time-picker
      :error-messages="errors['timestamp']"
      :value="datetime"
      :label="$t('ledger_action_form.date.label')"
      persistent-hint
      required
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
          :error-messages="errors['asset']"
          :value="action.asset"
          required
          :rules="assetRules"
          @input="updateAction('asset', $event)"
        />
      </v-col>

      <v-col cols="12" md="4">
        <v-text-field
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

    <v-text-field
      :error-messages="errors['link']"
      :value="action.link"
      :label="$t('ledger_action_form.link.label')"
      @input="updateAction('link', $event)"
    />

    <v-textarea
      :error-messages="errors['notes']"
      :value="action.notes"
      outlined
      :label="$t('ledger_action_form.notes.label')"
      @input="updateAction('notes', $event)"
    />
  </v-form>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import { ledgerActionsData } from '@/store/history/consts';
import { LedgerAction, UnsavedAction } from '@/store/history/types';
import { Properties } from '@/types';
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
  errors!: { [key in Properties<UnsavedAction, any>]?: string };

  @Emit()
  input(_value: boolean) {}

  @Emit('action:update')
  actionUpdate(_action: Action) {}

  @Watch('action')
  onActionUpdate(action: Action) {
    if (action.timestamp === 0) {
      this.datetime = '';
    } else {
      this.datetime = convertFromTimestamp(action.timestamp);
    }
  }

  onDateChange(date: string) {
    this.actionUpdate({ ...this.action, timestamp: convertToTimestamp(date) });
  }

  updateAction(prop: Properties<UnsavedAction, any>, value: string | null) {
    this.actionUpdate({ ...this.action, [prop]: value });
  }

  datetime: string = '';

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
  &__amount-wrapper {
    ::v-deep {
      .v-input {
        input {
          height: 60px;
          max-height: 60px !important;
        }
      }
    }
  }
}
</style>
