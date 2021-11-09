<template>
  <div class="d-flex flex-row align-center">
    <v-img
      aspect-ratio="1"
      contain
      position="left"
      width="26px"
      max-height="24px"
      :src="require(`@/assets/images/defi/${getIcon(item)}.svg`)"
    />
    <span class="ml-2">{{ identifier }}</span>
  </div>
</template>
<script lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { Component, Mixins, Prop } from 'vue-property-decorator';
import ScrambleMixin from '@/mixins/scramble-mixin';

type DefiProtocolInfo = {
  readonly identifier: string;
  readonly protocol: DefiProtocol;
};

@Component({})
export default class DefiSelectorItem extends Mixins(ScrambleMixin) {
  @Prop({ required: true })
  item!: DefiProtocolInfo;

  getIcon({ protocol }: DefiProtocolInfo): string {
    return protocol.startsWith('makerdao') ? 'makerdao' : protocol;
  }

  get identifier(): string {
    const { identifier } = this.item;
    if (this.scrambleData) {
      if (parseInt(identifier)) {
        return this.$tc('defi_selector_item.vault');
      } else if (identifier.includes('-')) {
        return identifier.split('-')[0];
      }
    }
    return identifier;
  }
}
</script>
