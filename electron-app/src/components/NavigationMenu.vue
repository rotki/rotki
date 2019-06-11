<template>
  <v-list>
    <v-list-tile to="/">
      <v-list-tile-action><v-icon>fa-dashboard</v-icon></v-list-tile-action>
      <v-list-tile-title>Dashboard</v-list-tile-title>
    </v-list-tile>
    <v-list-group prepend-icon="fa-exchange" value="true">
      <template v-slot:activator>
        <v-list-tile>
          <v-list-tile-title>Trade</v-list-tile-title>
        </v-list-tile>
      </template>

      <v-list-tile to="/otc-trades">
        <v-list-tile-title>OTC Trades</v-list-tile-title>
      </v-list-tile>
    </v-list-group>
    <v-list-tile to="/statistics">
      <v-list-tile-action><v-icon>fa-bar-chart</v-icon></v-list-tile-action>
      <v-list-tile-title>Statistics</v-list-tile-title>
    </v-list-tile>
    <v-list-tile to="/tax-report">
      <v-list-tile-action><v-icon>fa-calculator</v-icon></v-list-tile-action>
      <v-list-tile-title>Tax Report</v-list-tile-title>
    </v-list-tile>
  </v-list>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class NavigationMenu extends Vue {}
</script>

<style scoped></style>
