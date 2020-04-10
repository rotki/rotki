<template>
  <v-form v-model="valid">
    <asset-select v-model="asset" :rules="assetRules"></asset-select>
    <v-text-field label="Label" :rules="labelRules"></v-text-field>
    <v-text-field
      type="number"
      label="Amount"
      :rules="amountRules"
    ></v-text-field>
    <tag-input v-model="tags"></tag-input>
    <v-select v-model="location" label="Location" :items="locations"></v-select>
    <v-btn depressed color="primary" :disabled="!valid" @click="save">
      Save
    </v-btn>
  </v-form>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import TagInput from '@/components/inputs/TagInput.vue';
import { Location } from '@/services/types-common';

const { mapGetters } = createNamespacedHelpers('balances');
@Component({
  components: { TagInput, AssetSelect },
  computed: {
    ...mapGetters(['manualLabels'])
  }
})
export default class ManuallyTrackedForm extends Vue {
  valid: boolean = false;

  manualLabels!: string[];

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

  async save() {
    await this.$store.dispatch('balances/addManualBalance', {
      asset: this.asset,
      amount: this.amount,
      label: this.label,
      tags: this.tags,
      location: this.location
    });
  }
}
</script>

<style scoped></style>
