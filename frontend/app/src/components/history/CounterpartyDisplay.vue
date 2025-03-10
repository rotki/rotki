<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import { toHumanReadable } from '@rotki/common';

const props = defineProps<{
  counterparty: string;
}>();

const { counterparty } = toRefs(props);

const { getCounterpartyData } = useHistoryEventCounterpartyMappings();

const { isDark } = useRotkiTheme();

const data = getCounterpartyData(counterparty);
const imagePath = '/assets/images/protocols/';

const useDarkModeImage = computed(() => get(isDark) && get(data).darkmodeImage);

const counterpartyImageSrc = computed<string | undefined>(() => {
  const counterpartyVal = get(data);

  if (!counterpartyVal)
    return undefined;

  if (get(useDarkModeImage)) {
    return `${imagePath}/${counterpartyVal.darkmodeImage}`;
  }

  if (counterpartyVal.image) {
    return `${imagePath}/${counterpartyVal.image}`;
  }

  return undefined;
});
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
        v-else-if="counterpartyImageSrc"
        :src="counterpartyImageSrc"
        contain
        size="20px"
      />
    </div>
    <div class="uppercase text-sm">
      {{ toHumanReadable(data.label, 'sentence') }}
    </div>
  </div>
</template>
