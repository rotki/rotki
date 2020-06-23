<template>
  <v-list-item
    :id="`${name}_box`"
    :to="`/exchange-balances/${name}`"
    :ripple="false"
    class="exchange-box__item"
  >
    <v-list-item-avatar
      tile
      class="exchange-box__icon__exchange exchange-box__icon"
    >
      <v-img
        contain
        height="24"
        :title="name"
        :src="require(`@/assets/images/${name}.png`)"
      />
    </v-list-item-avatar>
    <v-list-item-content>
      <v-list-item-title class="d-flex justify-space-between">
        <span>
          {{ name | capitalize }}
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
export default class ExchangeBox extends Vue {
  @Prop({ required: true })
  name!: string;
  @Prop({ required: true })
  amount!: BigNumber;

  get inverted(): boolean {
    return ['bitmex', 'coinbasepro'].indexOf(this.name) > -1;
  }
}
</script>
<style scoped lang="scss">
.exchange-box {
  &__icon {
    filter: grayscale(100%);

    &__exchange {
      margin: 0;
      margin-right: 5px !important;
    }

    &--inverted {
      margin-left: 8px;
      width: 45px;
      filter: grayscale(100%) invert(100%);
    }
  }

  &__currency {
    &__symbol {
      font-size: 2em;
    }
  }

  &__item {
    &:hover {
      .exchange-box {
        &__icon {
          filter: grayscale(0);
        }
      }
    }
  }
}
</style>
