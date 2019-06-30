<template>
  <v-img :src="img(symbol)"></v-img>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class CryptoIcon extends Vue {
  @Prop({ required: true })
  symbol!: string;

  img(symbol: string): string {
    let url: string;
    let tokenSymbol: string;
    try {
      if (symbol === 'IOTA') {
        tokenSymbol = 'MIOTA';
      } else {
        tokenSymbol = symbol;
      }
      tokenSymbol = tokenSymbol.toLocaleLowerCase();
      url = require(`cryptocurrency-icons/svg/color/${tokenSymbol}.svg`);
    } catch (e) {
      url = require(`cryptocurrency-icons/svg/color/generic.svg`);
    }
    return url;
  }
}
</script>

<style scoped></style>
