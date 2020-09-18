<template>
  <div class="d-flex justify-space-between align-center text-h5">
    {{ title }}

    <span>
      <refresh-button
        :loading="loading"
        :tooltip="
          $t('helpers.refresh_header.tooltip', { title: lowercaseTitle })
        "
        @refresh="refresh()"
      />
      <slot />
    </span>
  </div>
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
