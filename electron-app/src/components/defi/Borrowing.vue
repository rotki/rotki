<template>
  <progress-screen v-if="loading">
    <template #message>
      Please wait while your balances are getting loaded...
    </template>
  </progress-screen>
  <v-container v-else>
    <v-row>
      <v-col cols="12">
        <h2>MakerDAO Vaults</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-select
          v-model="selection"
          class="borrowing__vault-selection"
          label="Vault"
          return-object
          :items="makerDAOVaults"
          item-text="name"
        ></v-select>
      </v-col>
    </v-row>
    <vault :vault="selection" />
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import Vault from '@/components/defi/Vault.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { MakerDAOVaultModel } from '@/store/balances/types';

const { mapGetters } = createNamespacedHelpers('balances');

@Component({
  computed: {
    ...mapGetters(['makerDAOVaults'])
  },
  components: { Vault, ProgressScreen }
})
export default class Borrowing extends Vue {
  loading: boolean = false;
  selection: MakerDAOVaultModel | null = null;
  makerDAOVaults!: MakerDAOVaultModel[];

  async mounted() {
    await this.$store.dispatch('balances/fetchMakerDAOVaults');
  }
}
</script>

<style scoped></style>
