<script setup lang="ts">
import { useLocations } from '@/modules/core/common/use-locations';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

const { location } = defineProps<{
  location: string;
}>();

defineSlots<{
  default: () => void;
}>();

const { useLocationData } = useLocations();

const locationData = useLocationData(() => location);
</script>

<template>
  <RuiBadge
    class="[&_span]:!px-0"
    color="default"
    offset-x="-8"
    offset-y="6"
  >
    <template #icon>
      <RuiTooltip
        :popper="{ placement: 'top', scroll: false, resize: false }"
        :open-delay="400"
      >
        <template #activator>
          <div class="rounded-full overflow-hidden bg-rui-grey-100 border-2 border-white dark:border-black size-6 flex items-center justify-center">
            <LocationIcon
              icon
              :item="location"
              size="20px"
            />
          </div>
        </template>
        <div class="capitalize">
          {{ locationData?.name ?? location }}
        </div>
      </RuiTooltip>
    </template>
    <slot />
  </RuiBadge>
</template>
