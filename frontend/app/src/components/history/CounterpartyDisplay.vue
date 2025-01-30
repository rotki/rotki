<script setup lang="ts">
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import AppImage from '@/components/common/AppImage.vue';

const props = defineProps<{
  counterparty: string;
}>();

const { counterparty } = toRefs(props);

const { getCounterpartyData } = useHistoryEventCounterpartyMappings();

const { isDark } = useRotkiTheme();

const data = getCounterpartyData(counterparty);
const imagePath = '/assets/images/protocols/';

const useDarkModeImage = computed(() => get(isDark) && get(data).darkmodeImage);
</script>

<template>
  <div class="flex items-center gap-3">
    <div
      :class="useDarkModeImage ? 'p-0.5 bg-black rounded-md' : 'icon-bg'"
    >
      <RuiIcon
        v-if="data.icon"
        :name="data.icon"
        :color="data.color || 'secondary'"
        size="20px"
      />

      <AppImage
        v-else-if="useDarkModeImage"
        :src="`${imagePath}${data.darkmodeImage}`"
        contain
        size="20px"
      />

      <AppImage
        v-else-if="data.image"
        :src="`${imagePath}${data.image}`"
        contain
        size="20px"
      />
    </div>
    <div class="uppercase text-sm">
      {{ toHumanReadable(data.label, 'sentence') }}
    </div>
  </div>
</template>
