<template>
  <v-img
    contain
    max-width="24px"
    max-height="24"
    class="mr-3"
    :src="require(`@/assets/images/defi/${protocol}.svg`)"
  />
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
