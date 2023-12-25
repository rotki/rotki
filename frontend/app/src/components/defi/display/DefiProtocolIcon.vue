<script setup lang="ts">
import { toSentenceCase } from '@/utils/text';
import { Module } from '@/types/modules';

const props = withDefaults(
  defineProps<{
    protocol: Module;
    mode?: 'icon' | 'label' | 'both';
  }>(),
  { mode: 'both' }
);
const protocol = toRef(props, 'protocol');

const icon = computed(() => {
  const defiProtocol = get(protocol);
  if (defiProtocol.endsWith('_v2')) {
    return defiProtocol.replace('_v2', '');
  }
  if (defiProtocol.startsWith('makerdao')) {
    return 'makerdao';
  }
  return defiProtocol;
});

const name = computed(() => {
  const defiProtocol = get(protocol);
  if (defiProtocol === Module.MAKERDAO_DSR) {
    return 'MakerDAO DSR';
  } else if (defiProtocol === Module.MAKERDAO_VAULTS) {
    return 'MakerDAO Vaults';
  } else if (defiProtocol === Module.YEARN) {
    return 'yearn.finance Vaults';
  } else if (defiProtocol === Module.YEARN_V2) {
    return 'yearn.finance Vaults v2';
  }
  return defiProtocol;
});

const css = useCssModule();
</script>

<template>
  <div
    class="flex flex-row items-center"
    :class="mode === 'icon' ? 'justify-center' : null"
  >
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :disabled="mode !== 'icon'"
      :open-delay="400"
    >
      <template #activator>
        <AppImage
          v-if="mode === 'icon' || mode === 'both'"
          contain
          max-width="32px"
          max-height="32px"
          :class="{
            'mr-2': mode !== 'icon',
            [css.icon]: true
          }"
          :src="`./assets/images/protocols/${icon}.svg`"
        />
        <span
          v-if="mode === 'label' || mode === 'both'"
          class="text--secondary"
          :class="css.label"
        >
          {{ toSentenceCase(name) }}
        </span>
      </template>
      <span>
        {{ toSentenceCase(name) }}
      </span>
    </RuiTooltip>
  </div>
</template>

<style lang="scss" module>
.icon {
  max-width: 30px;
}

.label {
  font-size: 12px;
}
</style>
