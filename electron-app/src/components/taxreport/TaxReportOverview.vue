<template>
  <v-layout>
    <v-flex>
      <v-card>
        <v-card-title>Overview</v-card-title>
        <v-card-text>
          <v-data-table></v-data-table>
        </v-card-text>
      </v-card>
    </v-flex>
  </v-layout>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class TaxReportOverview extends Vue {}
</script>

<style scoped></style>
