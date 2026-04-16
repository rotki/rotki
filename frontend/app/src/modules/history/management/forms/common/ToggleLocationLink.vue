<script setup lang="ts">
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

const modelValue = defineModel<string | undefined>({ required: true });

const { disabled, location } = defineProps<{
  location: string | undefined;
  disabled?: boolean;
}>();

const locationLimited = ref<boolean>(true);

const { getChainName, isDecodableChains, matchChain } = useSupportedChains();
const { t } = useI18n({ useScope: 'global' });

const isDisabled = computed<boolean>(() => {
  if (disabled || location === undefined) {
    return true;
  }

  const chain = matchChain(location);
  return !chain || !isDecodableChains(chain);
});

const tooltipText = computed<string>(() => {
  if (get(isDisabled)) {
    return t('toggle_location_link.disabled');
  }

  return get(locationLimited) && location
    ? t('toggle_location_link.limited', { location: getChainName(location) })
    : t('toggle_location_link.unlimited');
});

function updateModel() {
  if (!get(locationLimited) || !isDefined(location) || get(isDisabled)) {
    set(modelValue, undefined);
    return;
  }

  set(modelValue, location.replace(' ', '_'));
}

watch(locationLimited, () => {
  updateModel();
});

watchImmediate(() => location, () => {
  updateModel();
});
</script>

<template>
  <div class="pt-1">
    <RuiTooltip
      :disabled="disabled"
      :popper="{ placement: 'top-end' }"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          :disabled="isDisabled"
          @click="locationLimited = !locationLimited"
        >
          <RuiIcon :name="locationLimited ? 'lu-link-2' : 'lu-link-2-off'" />
        </RuiButton>
      </template>
      {{ tooltipText }}
    </RuiTooltip>
  </div>
</template>
