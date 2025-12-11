<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import { useLocations } from '@/composables/locations';

const props = withDefaults(
  defineProps<{
    item: string;
    horizontal?: boolean;
    icon?: boolean;
    size?: string;
    noPadding?: boolean;
  }>(),
  {
    horizontal: false,
    icon: false,
    noPadding: false,
    size: '24px',
  },
);

const emit = defineEmits<{ (e: 'click', location: string): void }>();

const { item } = toRefs(props);

const { locationData } = useLocations();

const location = locationData(item);
</script>

<template>
  <div
    class="flex items-center justify-center"
    data-cy="location-icon"
    :class="{
      'flex-row gap-2': horizontal,
      'flex-col gap-1': !horizontal,
      'skeleton': !location,
    }"
    :style="icon ? { height: size, width: size } : undefined"
    @click="emit('click', item)"
  >
    <template v-if="location">
      <AppImage
        v-if="location.image"
        :src="location.image"
        :alt="location.name"
        contain
        :size="size"
        class="icon-bg"
      />
      <div
        v-else
        class="icon-bg"
      >
        <RuiIcon
          v-if="location.icon"
          color="secondary"
          :size="size"
          :name="location.icon"
        />
      </div>

      <span
        v-if="!icon"
        class="capitalize text-rui-text-secondary"
        :class="{
          '-mb-1 text-center': !horizontal,
        }"
      >
        {{ location.name }}
      </span>
    </template>
  </div>
</template>
