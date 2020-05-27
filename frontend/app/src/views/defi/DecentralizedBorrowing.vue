<template>
  <v-container>
    <v-row>
      <v-col>
        <h1>Decentralized Borrowing</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <borrowing></borrowing>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import Borrowing from '@/components/defi/Borrowing.vue';

@Component({
  components: { Borrowing }
})
export default class DecentralizedBorrowing extends Vue {}
</script>

<style scoped></style>
