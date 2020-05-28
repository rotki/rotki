<template>
  <v-form ref="form" v-model="valid" class="manual-balances-form">
    <asset-select
      v-model="asset"
      class="manual-balances-form__asset"
      :rules="assetRules"
      :disabled="pending"
    ></asset-select>
    <v-text-field
      v-model="label"
      class="manual-balances-form__label"
      label="Label"
      :error-messages="errorMessages"
      :rules="labelRules"
      :disabled="pending || !!edit"
    ></v-text-field>
    <v-text-field
      v-model="amount"
      class="manual-balances-form__amount"
      type="number"
      label="Amount"
      :disabled="pending"
      :rules="amountRules"
    ></v-text-field>
    <tag-input
      v-model="tags"
      :disabled="pending"
      class="manual-balances-form__tags"
    ></tag-input>
    <v-select
      v-model="location"
      class="manual-balances-form__location"
      :disabled="pending"
      label="Location"
      :items="locations"
    >
      <template #item="{ item, attrs, on }">
        <v-list-item :id="`balance-location__${item}`" v-bind="attrs" v-on="on">
          {{ item }}
        </v-list-item>
      </template>
    </v-select>
    <v-btn
      class="manual-balances-form__save"
      depressed
      color="primary"
      :disabled="!valid || pending"
      @click="save"
    >
      Save
    </v-btn>
    <v-btn
      v-if="!!edit"
      depressed
      class="manual-balances-form__cancel"
      @click="clear"
    >
      Cancel
    </v-btn>
  </v-form>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import TagInput from '@/components/inputs/TagInput.vue';
import { Location } from '@/services/types-common';
import { ManualBalance } from '@/services/types-model';

const { mapGetters } = createNamespacedHelpers('balances');
@Component({
  components: { TagInput, AssetSelect },
  computed: {
    ...mapGetters(['manualLabels'])
  }
})
export default class ManualBalancesForm extends Vue {
  @Prop({ required: false, default: null })
  edit!: ManualBalance | null;

  @Watch('edit', { immediate: true })
  onEdit(balance: ManualBalance | null) {
    if (!balance) {
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
      this.errorMessages.push(`Label ${label} already exists`);
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
  location: Location = Location.EXTERNAL;

  get locations(): string[] {
    return Object.values(Location);
  }

  readonly amountRules = [(v: string) => !!v || 'The amount cannot be empty'];
  readonly assetRules = [(v: string) => !!v || 'The asset cannot be empty'];
  readonly labelRules = [(v: string) => !!v || 'The label cannot be empty'];

  @Emit()
  clear() {
    this.reset();
  }

  private reset() {
    (this.$refs?.form as any)?.reset();
    this.errorMessages.pop();
  }

  async save() {
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
    }
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
