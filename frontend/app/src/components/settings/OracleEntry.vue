<template>
  <v-row align="center">
    <v-col cols="4">
      <v-img
        :width="size"
        contain
        position="left"
        :max-height="size"
        :src="icon"
      />
    </v-col>
    <v-col>
      {{ capitalize(identifier) }}
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class OracleEntry extends Vue {
  @Prop({ required: true, type: String })
  identifier!: string;

  size = '48px';

  get icon(): string {
    if (this.identifier === 'cryptocompare') {
      return require('@/assets/images/oracles/cryptocompare.png');
    } else if (this.identifier === 'coingecko') {
      return require('@/assets/images/oracles/coingecko.svg');
    } else if (this.identifier === 'manual') {
      this.size = '40px';
      return require('@/assets/images/oracles/book.svg');
    }
    return '';
  }

  capitalize(text: string) {
    return text[0].toUpperCase() + text.slice(1);
  }
}
</script>

<style scoped lang="scss"></style>
