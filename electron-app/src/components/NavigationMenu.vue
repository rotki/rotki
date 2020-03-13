<template>
  <v-list>
    <v-list-item to="/" class="navigation__dashboard">
      <v-list-item-action><v-icon>fa-dashboard</v-icon></v-list-item-action>
      <v-list-item-content>
        <v-list-item-title>Dashboard</v-list-item-title>
      </v-list-item-content>
    </v-list-item>
    <v-list-item
      to="/blockchain-accounts"
      class="navigation__accounts-balances"
    >
      <v-list-item-action><v-icon>fa-user</v-icon></v-list-item-action>
      <v-list-item-content>
        <v-list-item-title>Accounts & Balances</v-list-item-title>
      </v-list-item-content>
    </v-list-item>
    <v-list-item to="/settings/api-keys" class="navigation__api-keys">
      <v-list-item-action><v-icon>fa-key</v-icon></v-list-item-action>
      <v-list-item-content>
        <v-list-item-title>API Keys</v-list-item-title>
      </v-list-item-content>
    </v-list-item>
    <v-list-item to="/import" class="navigation__import">
      <v-list-item-action><v-icon>fa-download</v-icon></v-list-item-action>
      <v-list-item-content>
        <v-list-item-title>Import Data</v-list-item-title>
      </v-list-item-content>
    </v-list-item>
    <v-list-group
      prepend-icon="fa-exchange"
      value="true"
      class="navigation__trades"
    >
      <template #activator>
        <v-list-item>
          <v-list-item-content>
            <v-list-item-title>Trade</v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </template>

      <v-list-item to="/otc-trades" class="navigation__otc-trades">
        <v-list-item-content>
          <v-list-item-title>OTC Trades</v-list-item-title>
        </v-list-item-content>
      </v-list-item>
    </v-list-group>
    <v-list-group
      prepend-icon="fa-line-chart"
      value="true"
      class="navigation__defi"
    >
      <template #activator>
        <v-list-item>
          <v-list-item-content>
            <v-list-item-title>Decentralized Finance</v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </template>

      <v-list-item to="/defi/loans" class="navigation__defi__loans">
        <v-list-item-content>
          <v-list-item-title>Loans</v-list-item-title>
        </v-list-item-content>
      </v-list-item>
    </v-list-group>
    <v-list-item to="/statistics" class="navigation__statistics">
      <v-list-item-action><v-icon>fa-bar-chart</v-icon></v-list-item-action>
      <v-list-item-content>
        <v-list-item-title>Statistics</v-list-item-title>
      </v-list-item-content>
    </v-list-item>
    <v-list-item to="/tax-report" class="navigation__tax-report">
      <v-list-item-action><v-icon>fa-calculator</v-icon></v-list-item-action>
      <v-list-item-content>
        <v-list-item-title>Tax Report</v-list-item-title>
      </v-list-item-content>
    </v-list-item>
  </v-list>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class NavigationMenu extends Vue {}
</script>

<style scoped lang="scss">
::v-deep {
  .v-list-group__header {
    &__append-icon {
      margin-left: -18px !important;
    }
    .v-list-item {
      padding-left: 0 !important;
    }
  }
}
</style>
