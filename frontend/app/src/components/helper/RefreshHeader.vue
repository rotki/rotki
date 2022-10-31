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
            :tooltip="tc('helpers.refresh_header.tooltip', 0, tooltip)"
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

<script setup lang="ts">
import RefreshButton from '@/components/helper/RefreshButton.vue';

const props = defineProps({
  title: { required: true, type: String },
  loading: { required: true, type: Boolean }
});

const emit = defineEmits(['refresh']);

const { title } = toRefs(props);
const { tc } = useI18n();

const tooltip = computed(() => ({
  title: get(title).toLocaleLowerCase()
}));

const refresh = () => {
  emit('refresh');
};
</script>
