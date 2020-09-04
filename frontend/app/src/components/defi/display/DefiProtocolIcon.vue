<template>
  <div class="defi-protocol-icon d-flex flex-row">
    <v-img
      v-if="mode === 'icon' || mode === 'both'"
      contain
      max-width="24px"
      max-height="24"
      class="defi-protocol-icon__image mr-3"
      :src="require(`@/assets/images/defi/${protocol}.svg`)"
    />
    <span
      v-if="mode === 'label' || mode === 'both'"
      class="defi-protocol-icon__label align-self-center"
    >
      {{ protocol === 'makerdao' ? 'MakerDAO DSR' : protocol | capitalize }}
    </span>
  </div>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { SupportedDefiProtocols } from '@/services/defi/types';

@Component({})
export default class DefiProtocolIcon extends Vue {
  @Prop({ required: true, type: String })
  protocol!: SupportedDefiProtocols;
  @Prop({ required: false, type: String, default: 'both' })
  mode!: 'icon' | 'label' | 'both';
}
</script>
