<template>
  <v-form ref="form" :value="valid" class="manual-balances-form" @input="input">
    <v-text-field
      v-model="label"
      class="manual-balances-form__label"
      :label="$t('manual_balances_form.fields.label')"
      :error-messages="errorMessages"
      :rules="labelRules"
      :disabled="pending || !!edit"
    />
    <asset-select
      v-model="asset"
      :label="$t('manual_balances_form.fields.asset')"
      class="manual-balances-form__asset"
      :rules="assetRules"
      :disabled="pending"
    />
    <v-text-field
      v-model="amount"
      :label="$t('manual_balances_form.fields.amount')"
      class="manual-balances-form__amount"
      type="number"
      autocomplete="off"
      :disabled="pending"
      :rules="amountRules"
    />
    <tag-input
      v-model="tags"
      :label="$t('manual_balances_form.fields.tags')"
      :disabled="pending"
      class="manual-balances-form__tags"
    />
    <location-selector
      v-model="location"
      class="manual-balances-form__location"
      :disabled="pending"
      :label="$t('manual_balances_form.fields.location')"
    />
  </v-form>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import TagInput from '@/components/inputs/TagInput.vue';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { ManualBalance } from '@/services/balances/types';
import { TradeLocation } from '@/services/history/types';

@Component({
  components: { LocationSelector, TagInput, AssetSelect },
  computed: {
    ...mapGetters('balances', ['manualLabels'])
  }
})
export default class ManualBalancesForm extends Vue {
  @Prop({ required: false, default: null })
  edit!: ManualBalance | null;
  @Prop({ required: true, type: Boolean })
  value!: boolean;

  @Watch('edit', { immediate: true })
  onEdit(balance: ManualBalance | null) {
    if (!balance) {
      this.reset();
      return;
    }
    this.asset = balance.asset;
    this.label = balance.label;
    this.amount = balance.amount.toString();
    this.tags = balance.tags;
    this.location = balance.location;
  }

  @Watch('label')
  onLabel(label: string) {
    if (this.edit) {
      return;
    }

    if (this.manualLabels.includes(label)) {
      if (this.errorMessages.length > 0) {
        return;
      }
      this.errorMessages.push(
        this.$tc('manual_balances_form.validation.label_exists', 0, { label })
      );
    } else {
      this.errorMessages.pop();
    }
  }

  valid: boolean = false;
  pending: boolean = false;

  manualLabels!: string[];
  errorMessages: string[] = [];

  asset: string = '';
  label: string = '';
  amount: string = '';
  tags: string[] = [];
  location: TradeLocation = TRADE_LOCATION_EXTERNAL;

  readonly amountRules = [
    (v: string) => !!v || this.$t('manual_balances_form.validation.amount')
  ];
  readonly assetRules = [
    (v: string) => !!v || this.$t('manual_balances_form.validation.asset')
  ];
  readonly labelRules = [
    (v: string) => !!v || this.$t('manual_balances_form.validation.label_empty')
  ];

  @Emit()
  clear() {
    this.reset();
  }

  @Emit()
  input(_valid: boolean) {}

  private reset() {
    (this.$refs?.form as any)?.reset();
    this.errorMessages.pop();
  }

  async save(): Promise<boolean> {
    this.pending = true;
    const action =
      this.edit === null ? 'addManualBalance' : 'editManualBalance';
    const success: boolean = await this.$store.dispatch(`balances/${action}`, {
      asset: this.asset,
      amount: this.amount,
      label: this.label,
      tags: this.tags,
      location: this.location
    });
    this.pending = false;
    if (success) {
      this.clear();
      this.reset();
      return true;
    }
    return false;
  }
}
</script>

<style scoped lang="scss">
.manual-balances-form {
  &__save {
    margin-right: 8px;
  }
}
</style>
