<template>
  <v-img
    v-if="isExchange"
    contain
    height="24"
    :title="name"
    :src="require(`@/assets/images/${name}.png`)"
  />
  <v-icon v-else>
    mdi-{{ manualBalanceIcons[name.replace(/\s+/g, '')] }}
  </v-icon>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class BalanceLocationIcon extends Vue {
  @Prop({ required: true })
  name!: string;

  manualBalanceIcons = {
    external: 'book',
    banks: 'bank',
    equities: 'bag-suitcase',
    realestate: 'home',
    commodities: 'basket',
    blockchain: 'link'
  };

  get isExchange() {
    return !Object.keys(this.manualBalanceIcons).includes(this.name);
  }
}
</script>
