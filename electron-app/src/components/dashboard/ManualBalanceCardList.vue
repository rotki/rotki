<template>
  <v-list-item
    :id="`${name}_box`"
    :ripple="false"
    class="manual-balance-box__item"
    @click="doNothing"
  >
    <v-list-item-avatar tile class="manual-balance-box__icon">
      <v-icon>
        fa fa-{{ manualBalanceIcons[name.replace(/\s+/g, '')] }}
      </v-icon>
    </v-list-item-avatar>
    <v-list-item-content>
      <v-list-item-title style="display: flex; justify-content: space-between;">
        <span>
          {{ name[0].toUpperCase() + name.slice(1) }}
        </span>
        <span class="text-end">
          <amount-display
            show-currency="symbol"
            fiat-currency="USD"
            :value="amount"
          ></amount-display>
        </span>
      </v-list-item-title>
    </v-list-item-content>
  </v-list-item>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import AmountDisplay from '@/components/display/AmountDisplay.vue';

@Component({
  components: { AmountDisplay }
})
export default class ManualBalanceCardList extends Vue {
  @Prop({ required: true })
  name!: string;
  @Prop({ required: true })
  amount!: BigNumber;

  manualBalanceIcons = {
    external: 'book',
    banks: 'bank',
    equities: 'suitcase',
    realestate: 'home',
    commodities: 'shopping-basket',
    fiat: 'money',
    blockchain: 'link'
  };

  doNothing() {}
}
</script>
<style scoped lang="scss">
.manual-balance-box__currency__symbol {
  font-size: 2em;
}

.manual-balance-box__icon {
  filter: grayscale(100%);
}

.manual-balance-box__item:hover .manual-balance-box__icon {
  filter: grayscale(0);
}

.manual-balance-box__icon--inverted {
  margin-left: 8px;
  width: 45px;
  filter: grayscale(100%) invert(100%);
}
</style>
