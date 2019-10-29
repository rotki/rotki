<template>
  <v-list>
    <v-list-item to="/">
      <v-list-item-action><v-icon>fa-dashboard</v-icon></v-list-item-action>
      <v-list-item-title>Dashboard</v-list-item-title>
    </v-list-item>
    <v-list-item to="/import">
      <v-list-item-action><v-icon>fa-download</v-icon></v-list-item-action>
      <v-list-item-title>Import Data</v-list-item-title>
    </v-list-item>
    <v-list-group prepend-icon="fa-exchange" value="true">
      <template #activator>
        <v-list-item>
          <v-list-item-title>Trade</v-list-item-title>
        </v-list-item>
      </template>

      <v-list-item to="/otc-trades">
        <v-list-item-title>OTC Trades</v-list-item-title>
      </v-list-item>
    </v-list-group>
    <v-list-item to="/statistics">
      <v-list-item-action><v-icon>fa-bar-chart</v-icon></v-list-item-action>
      <v-list-item-title>Statistics</v-list-item-title>
    </v-list-item>
    <v-list-item to="/tax-report">
      <v-list-item-action><v-icon>fa-calculator</v-icon></v-list-item-action>
      <v-list-item-title>Tax Report</v-list-item-title>
    </v-list-item>
  </v-list>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class NavigationMenu extends Vue {}
</script>

<style scoped></style>
