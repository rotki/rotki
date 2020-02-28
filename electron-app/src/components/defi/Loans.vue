<template>
  <v-card>
    <v-card-title>
      MakerDAO DSR
    </v-card-title>
    <v-card-text></v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Vue } from 'vue-property-decorator';
import Component from 'vue-class-component';

@Component({})
export default class Loans extends Vue {
  async mount() {
    await this.$store.dispatch('balances/fetchDSRData');
    console.log('d')
  }
}
</script>

<style scoped lang="scss"></style>
