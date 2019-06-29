<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <v-menu id="balances-saved-dropdown" transition="slide-y-transition" bottom>
    <template v-slot:activator="{ on }">
      <v-btn color="primary" dark icon flat v-on="on">
        <v-icon>
          fa fa-fw fa-save
        </v-icon>
        <v-icon>fa fa-caret-down</v-icon>
      </v-btn>
    </template>
    <v-layout column class="popup">
      <v-layout row>
        Balances last saved
      </v-layout>
      <v-layout id="last_balance_save_field" row class="text--secondary">
        Never
      </v-layout>
    </v-layout>
  </v-menu>
</template>
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class BalanceSavedIndicator extends Vue {}
</script>

<style lang="scss" scoped>
.popup {
  background: white;
  padding: 16px;
}
</style>
