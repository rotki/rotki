<template>
  <span>
    <v-img
      width="55px"
      contain
      max-height="24px"
      :src="require(`@/assets/images/defi/${protocol}.svg`)"
    />
  </span>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { SupportedDefiProtocols } from '@/services/defi/types';

@Component({})
export default class DefiProtocolIcon extends Vue {
  @Prop({ required: true, type: String })
  protocol!: SupportedDefiProtocols;
}
</script>
