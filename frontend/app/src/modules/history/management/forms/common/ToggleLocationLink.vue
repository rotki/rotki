<script setup lang="ts">
import { useSupportedChains } from '@/composables/info/chains';

const modelValue = defineModel<string | undefined>({ required: true });

const props = withDefaults(defineProps<{
  location: string | undefined;
  disabled?: boolean;
}>(), { disabled: false });

const locationLimited = ref<boolean>(true);

const { matchChain } = useSupportedChains();
const { t } = useI18n({ useScope: 'global' });

const isDisabled = computed<boolean>(() => props.disabled || props.location === undefined || !matchChain(props.location));

const tooltipText = computed<string>(() => {
  if (get(isDisabled)) {
    return t('toggle_location_link.disabled');
  }

  return get(locationLimited)
    ? t('toggle_location_link.limited', { location: props.location })
    : t('toggle_location_link.unlimited');
});

function updateModel() {
  const location = props.location;
  if (!get(locationLimited) || location === undefined || !matchChain(location)) {
    set(modelValue, undefined);
  }
  else {
    set(modelValue, location.replace(' ', '_'));
  }
}

watch(locationLimited, () => {
  updateModel();
});

watchImmediate(() => props.location, () => {
  updateModel();
});
</script>

<template>
  <div class="pt-1">
    <RuiTooltip :disabled="disabled">
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
