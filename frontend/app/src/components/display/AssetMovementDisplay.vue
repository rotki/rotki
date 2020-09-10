<template>
  <v-row align="center" justify="end" no-gutters class="grow">
    <balance-display :asset="movement.asset" :value="movement.value" />
    <v-col sm="12" md="auto" cols="12" class="mr-2">
      <v-icon>mdi-chevron-right</v-icon>
    </v-col>
    <balance-display :asset="movement.toAsset" :value="movement.toValue" />
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import { AssetMovement } from '@/components/display/types';

@Component({
  components: { BalanceDisplay }
})
export default class AssetMovementDisplay extends Vue {
  @Prop({ required: true })
  movement!: AssetMovement;
}
</script>
