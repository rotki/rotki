<template>
  <v-menu id="balances-saved-dropdown" transition="slide-y-transition" bottom>
    <template #activator="{ on }">
      <v-btn color="primary" dark icon text v-on="on">
        <v-icon>
          fa fa-save
        </v-icon>
      </v-btn>
    </template>
    <v-row column class="popup">
      <v-row>
        Balances last saved
      </v-row>
      <v-row id="last_balance_save_field" class="text--secondary">
        Never
      </v-row>
    </v-row>
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
