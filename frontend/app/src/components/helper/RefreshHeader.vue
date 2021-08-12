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
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import RefreshButton from '@/components/helper/RefreshButton.vue';

export default defineComponent({
  name: 'RefreshHeader',
  components: { RefreshButton },
  props: {
    title: { required: true, type: String },
    loading: { required: true, type: Boolean }
  },
  setup(props, { emit }) {
    const { title } = toRefs(props);
    const refresh = () => {
      emit('refresh');
    };
    const lowercaseTitle = computed(() => {
      return title.value.toLocaleLowerCase();
    });
    return {
      refresh,
      lowercaseTitle
    };
  },
  computed: {
    xsOnly(): boolean {
      return this.$vuetify.breakpoint.xsOnly;
    }
  }
});
</script>
