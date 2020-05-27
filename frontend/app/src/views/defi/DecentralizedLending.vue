<template>
  <v-container>
    <v-row>
      <v-col>
        <h1>Decentralized Lending</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <lending></lending>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import Lending from '@/components/defi/Lending.vue';

@Component({
  components: { Lending }
})
export default class DecentralizedLoans extends Vue {}
</script>

<style scoped></style>
