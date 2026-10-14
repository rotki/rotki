<script setup lang="ts">
import { useLocations } from '@/modules/core/common/use-locations';
import { useSetting } from '@/modules/settings/use-setting';
import IconMark from '@/modules/shell/components/IconMark.vue';

const { item, horizontal, icon, size = '24px' } = defineProps<{
  item: string;
  horizontal?: boolean;
  icon?: boolean;
  size?: string;
}>();

const emit = defineEmits<{
  click: [location: string];
}>();

const { useLocationData } = useLocations();
const shouldShowAmount = useSetting('shouldShowAmount');

const location = useLocationData(() => item);
</script>

<template>
  <div
    class="flex items-center"
    data-testid="location-icon"
    :class="{
      'flex-row gap-2': horizontal,
      'flex-col justify-center gap-1': !horizontal,
      'skeleton': !location,
      'blur': !shouldShowAmount,
    }"
    :style="icon ? { height: size, width: size } : undefined"
    @click="emit('click', item)"
  >
    <template v-if="location">
      <IconMark
        v-if="location.image"
        :src="location.image"
        :alt="location.name"
        :size="size"
      />
      <RuiIcon
        v-else-if="location.icon"
        color="secondary"
        :size="size"
        :name="location.icon"
      />

      <span
        v-if="!icon"
        class="capitalize"
        :class="horizontal ? 'text-rui-text truncate' : '-mb-1 text-center text-rui-text-secondary'"
      >
        {{ location.name }}
      </span>
    </template>
  </div>
</template>
