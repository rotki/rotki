<template>
  <v-container>
    <v-row no-gutters>
      <v-col>
        <h2>Borrowing</h2>
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
