<template>
  <v-container>
    <v-row>
      <v-col>
        <h1>Decentralized Loans</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <loans></loans>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import Loans from '@/components/defi/Loans.vue';

@Component({
  components: { Loans }
})
export default class DecentralizedLoans extends Vue {}
</script>

<style scoped></style>
