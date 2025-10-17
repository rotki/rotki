<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import EnsAvatar from '@/components/display/EnsAvatar.vue';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import { getPublicProtocolImagePath } from '@/utils/file';

const props = defineProps<{
  event: { counterparty: string | null; address?: string | null };
}>();

const { event } = toRefs(props);

const { getEventCounterpartyData } = useHistoryEventCounterpartyMappings();

const { isDark } = useRotkiTheme();

const counterparty = getEventCounterpartyData(event);

const useDarkModeImage = computed(() => get(isDark) && get(counterparty)?.darkmodeImage);
const counterpartyImageSrc = computed<string | undefined>(() => {
  const counterpartyVal = get(counterparty);

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
</script>

<template>
  <RuiBadge
    v-if="counterparty || event.address"
    class="[&_span]:!px-0"
    color="default"
    offset-x="-6"
    offset-y="6"
  >
    <template #icon>
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <div
            class="rounded-full overflow-hidden bg-rui-grey-100 border-2 border-white dark:border-black size-6 flex items-center justify-center"
            :class="{ '!bg-black': useDarkModeImage }"
          >
            <template v-if="counterparty">
              <RuiIcon
                v-if="counterparty.icon"
                :name="counterparty.icon"
                :color="counterparty.color"
              />

              <AppImage
                v-else-if="counterpartyImageSrc"
                :src="counterpartyImageSrc"
                contain
                size="20px"
              />

              <EnsAvatar
                v-else
                size="20px"
                :address="counterparty.label"
              />
            </template>
            <EnsAvatar
              v-else-if="event.address"
              size="20px"
              :address="event.address"
              avatar
            />
          </div>
        </template>
        <div>{{ counterparty?.label || event?.address }}</div>
      </RuiTooltip>
    </template>
    <slot />
  </RuiBadge>
  <div v-else>
    <slot />
  </div>
</template>
