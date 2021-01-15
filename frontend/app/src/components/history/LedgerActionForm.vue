<template>
  <v-form :value="value" @input="input">
    <location-selector
      v-model="location"
      :rules="locationRules"
      :label="$t('ledger_action_form.location.label')"
    />
    <date-time-picker
      v-model="datetime"
      :label="$t('ledger_action_form.date.label')"
      persistent-hint
      required
      :hint="$t('ledger_action_form.date.hint')"
    />
    <v-row>
      <v-col cols="12" md="4">
        <asset-select v-model="asset" required :rules="assetRules" />
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model="amount"
          :rules="amountRules"
          type="number"
          required
          :label="$t('ledger_action_form.amount.label')"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-select
          v-model="actionType"
          :label="$t('ledger_action_form.type.label')"
          :items="typeData"
          item-value="identifier"
          item-text="label"
          required
        />
      </v-col>
    </v-row>

    <v-text-field v-model="link" :label="$t('ledger_action_form.link.label')" />
    <v-textarea
      v-model="notes"
      outlined
      :label="$t('ledger_action_form.notes.label')"
    />
  </v-form>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { TradeLocation } from '@/services/history/types';
import { ACTION_INCOME, ledgerActionsData } from '@/store/history/consts';
import { LedgerActionType } from '@/store/history/types';

@Component({
  components: { LocationSelector }
})
export default class LedgerActionForm extends Vue {
  @Prop({ required: false, type: Boolean, default: false })
  value!: boolean;

  @Emit()
  input(_value: boolean) {}

  location: TradeLocation | null = TRADE_LOCATION_EXTERNAL;
  actionType: LedgerActionType = ACTION_INCOME;
  datetime: string = '';
  asset: string = '';
  link: string = '';
  amount: string = '';
  notes: string = '';

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

<style scoped lang="scss"></style>
