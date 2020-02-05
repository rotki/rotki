<template>
  <v-menu id="balances-saved-dropdown" transition="slide-y-transition" bottom>
    <template #activator="{ on }">
      <v-btn color="primary" dark icon text v-on="on">
        <v-icon>
          fa fa-save
        </v-icon>
      </v-btn>
    </template>
    <div class="balance-saved-indicator__content">
      <v-row>
        Balances last saved
      </v-row>
      <v-row class="text--secondary">
        <span v-if="lastBalanceSave">
          {{ lastBalanceSave | formatDate(dateDisplayFormat) }}
        </span>
        <span v-else>
          Never
        </span>
      </v-row>
    </div>
  </v-menu>
</template>
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';

const { mapGetters } = createNamespacedHelpers('session');

@Component({
  computed: {
    ...mapGetters(['lastBalanceSave', 'dateDisplayFormat'])
  }
})
export default class BalanceSavedIndicator extends Vue {
  lastBalanceSave!: number;
  dateDisplayFormat!: string;
}
</script>

<style lang="scss" scoped>
.balance-saved-indicator__content {
  background: white;
  width: 280px;
  padding: 16px;
}

.balance-saved-indicator__content > * {
  padding: 4px 16px;
}
</style>
