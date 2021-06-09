<template>
  <v-form ref="form" :value="valid" class="manual-balances-form" @input="input">
    <v-text-field
      v-model="label"
      class="manual-balances-form__label"
      outlined
      :label="$t('manual_balances_form.fields.label')"
      :error-messages="errors['label']"
      :rules="labelRules"
      :disabled="pending || !!edit"
      @focus="delete errors['label']"
    />
    <asset-select
      v-model="asset"
      :label="$t('manual_balances_form.fields.asset')"
      :error-messages="errors['asset']"
      class="manual-balances-form__asset"
      outlined
      :rules="assetRules"
      :disabled="pending"
      @focus="delete errors['asset']"
    />
    <v-text-field
      v-model="amount"
      :label="$t('manual_balances_form.fields.amount')"
      :error-messages="errors['amount']"
      class="manual-balances-form__amount"
      outlined
      type="number"
      autocomplete="off"
      :disabled="pending"
      :rules="amountRules"
      @focus="delete errors['amount']"
    />
    <tag-input
      v-model="tags"
      :label="$t('manual_balances_form.fields.tags')"
      :disabled="pending"
      outlined
      class="manual-balances-form__tags"
    />
    <location-selector
      v-model="location"
      class="manual-balances-form__location"
      outlined
      :error-messages="errors['location']"
      :disabled="pending"
      :label="$t('manual_balances_form.fields.location')"
      @focus="delete errors['location']"
    />
  </v-form>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import TagInput from '@/components/inputs/TagInput.vue';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { ManualBalance } from '@/services/balances/types';
import { deserializeApiErrorMessage } from '@/services/converters';
import { TradeLocation } from '@/services/history/types';
import { ActionStatus } from '@/store/types';
import { bigNumberify } from '@/utils/bignumbers';

@Component({
  components: { LocationSelector, TagInput, AssetSelect },
  computed: {
    ...mapGetters('balances', ['manualLabels'])
  },
  methods: {
    ...mapActions('balances', ['addManualBalance', 'editManualBalance'])
  }
})
export default class ManualBalancesForm extends Vue {
  @Prop({ required: false, default: null })
  edit!: ManualBalance | null;
  @Prop({ required: true, type: Boolean })
  value!: boolean;

  editManualBalance!: (balance: ManualBalance) => Promise<ActionStatus>;
  addManualBalance!: (balance: ManualBalance) => Promise<ActionStatus>;

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

    const errors = this.errors['label'];
    if (this.manualLabels.includes(label)) {
      if (errors && errors.length > 0) {
        return;
      }
      this.errors['label'] = [
        this.$tc('manual_balances_form.validation.label_exists', 0, { label })
      ];
    } else {
      delete this.errors['label'];
    }
  }

  valid: boolean = false;
  pending: boolean = false;

  manualLabels!: string[];
  errors: { [key: string]: string[] } = {};

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
    this.errors = {};
  }

  async save(): Promise<boolean> {
    this.pending = true;
    const balance: ManualBalance = {
      asset: this.asset,
      amount: bigNumberify(this.amount),
      label: this.label,
      tags: this.tags,
      location: this.location
    };
    const status = await (this.edit
      ? this.editManualBalance(balance)
      : this.addManualBalance(balance));

    this.pending = false;

    if (status.success) {
      this.clear();
      this.reset();
      return true;
    }

    if (status.message) {
      const errorMessages = deserializeApiErrorMessage(status.message);
      this.errors = (errorMessages?.balances[0] as any) ?? {};
    }
    return false;
  }
}
</script>

<style scoped lang="scss">
.manual-balances-form {
  padding-top: 12px;

  &__save {
    margin-right: 8px;
  }
}
</style>
