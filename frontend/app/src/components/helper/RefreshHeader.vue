<template>
  <v-row justify="space-between" align="center" no-gutters>
    <v-col>
      <card-title>{{ title }}</card-title>
    </v-col>
    <v-col cols="auto">
      <v-row no-gutters>
        <v-col v-if="$slots.actions" cols="auto" class="px-1">
          <slot name="actions" />
        </v-col>
        <v-col cols="auto" class="px-1">
          <refresh-button
            :loading="loading"
            :tooltip="
              $t('helpers.refresh_header.tooltip', { title: lowercaseTitle })
            "
            @refresh="refresh()"
          />
        </v-col>
        <v-col v-if="$slots.default" cols="auto" class="px-1">
          <slot />
        </v-col>
      </v-row>
    </v-col>
  </v-row>
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
