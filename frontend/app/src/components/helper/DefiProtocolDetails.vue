<template>
  <span v-bind="$attrs" class="d-flex flex-row align-center">
    <v-img
      width="26px"
      contain
      position="left"
      max-height="24px"
      :src="item.icon"
    />
    <span class="ml-1">{{ item.name }}</span>
  </span>
</template>
<script lang="ts">
import { Prop, Vue, Component } from 'vue-property-decorator';

@Component({})
export default class DefiProtocolDetails extends Vue {
  @Prop({ required: true })
  item!: { icon: string; name: string };
}
</script>
