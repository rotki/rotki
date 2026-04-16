<script setup lang="ts">
import { useLocations } from '@/modules/core/common/use-locations';
import AppImage from '@/modules/shell/components/AppImage.vue';

const { item, horizontal, icon, size = '24px', imageClass } = defineProps<{
  item: string;
  horizontal?: boolean;
  icon?: boolean;
  size?: string;
  imageClass?: string;
}>();

const emit = defineEmits<{
  click: [location: string];
}>();

const { useLocationData } = useLocations();

const location = useLocationData(() => item);
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
        :image-class="imageClass"
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
