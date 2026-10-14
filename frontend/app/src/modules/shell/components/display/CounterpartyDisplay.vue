<script setup lang="ts">
import { toHumanReadable } from '@rotki/common';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import IconMark from '@/modules/shell/components/IconMark.vue';

const { counterparty, icon, size = '20px' } = defineProps<{
  counterparty: string;
  icon?: boolean;
  size?: string;
}>();

const { getCounterpartyData } = useHistoryEventCounterpartyMappings();

const { isDark } = useRotkiTheme();

const data = getCounterpartyData(() => counterparty);

const useDarkModeImage = computed(() => get(isDark) && get(data).darkmodeImage);

const counterpartyImageSrc = computed<string | undefined>(() => {
  const counterpartyVal = get(data);

  if (!counterpartyVal)
    return undefined;

  if (get(useDarkModeImage)) {
    return getPublicProtocolImagePath(counterpartyVal.darkmodeImage!);
  }

  if (counterpartyVal.image) {
    return getPublicProtocolImagePath(counterpartyVal.image);
  }

  return undefined;
});

/** A protocol whose logo is missing shows a generic mark rather than an empty circle. */
const imageFailed = ref<boolean>(false);

watch(counterpartyImageSrc, () => {
  set(imageFailed, false);
});
</script>

<template>
  <div class="flex items-center gap-2 text-rui-text text-sm">
    <RuiIcon
      v-if="data.icon"
      :name="data.icon"
      :color="data.color || 'secondary'"
      :size="size"
    />
    <IconMark
      v-else-if="counterpartyImageSrc && !imageFailed"
      :src="counterpartyImageSrc"
      :size="size"
      :backing="useDarkModeImage ? 'dark' : 'light'"
      @error="imageFailed = true"
    />
    <RuiIcon
      v-else
      name="lu-blocks"
      color="secondary"
      :size="size"
    />
    <div
      v-if="!icon"
      class="uppercase"
    >
      {{ toHumanReadable(data.label, 'sentence') }}
    </div>
  </div>
</template>
