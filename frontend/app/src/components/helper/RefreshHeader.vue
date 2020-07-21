<template>
  <h2 class="d-flex justify-space-between align-center">
    {{ title }}

    <span>
      <refresh-button
        :loading="loading"
        :refresh="refresh"
        :tooltip="
          $t('helpers.refresh_header.tooltip', { title: lowercaseTitle })
        "
      />
      <slot />
    </span>
  </h2>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import RefreshButton from '@/components/helper/RefreshButton.vue';

@Component({
  components: { RefreshButton }
})
export default class RefreshHeader extends Vue {
  @Prop({ required: true, type: String })
  title!: string;

  @Prop({ required: true, type: Boolean })
  loading!: boolean;

  get lowercaseTitle(): string {
    return this.title.toLocaleLowerCase();
  }

  @Emit()
  refresh() {}
}
</script>
