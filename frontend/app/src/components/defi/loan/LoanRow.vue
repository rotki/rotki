<template>
  <div
    class="d-flex justify-space-between py-1"
    :class="medium ? 'font-weight-medium' : ''"
  >
    <div>
      {{ title }}
    </div>
    <div>
      <slot />
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class LoanRow extends Vue {
  @Prop({ required: false, type: String, default: '' })
  title!: string;
  @Prop({ required: false, type: Boolean, default: true })
  medium!: boolean;
}
</script>

<style scoped></style>
