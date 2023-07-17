<script setup lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { toSentenceCase } from '@/utils/text';

const props = withDefaults(
  defineProps<{
    protocol: DefiProtocol;
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
  if (defiProtocol === DefiProtocol.MAKERDAO_DSR) {
    return 'MakerDAO DSR';
  } else if (defiProtocol === DefiProtocol.MAKERDAO_VAULTS) {
    return 'MakerDAO Vaults';
  } else if (defiProtocol === DefiProtocol.YEARN_VAULTS) {
    return 'yearn.finance Vaults';
  } else if (defiProtocol === DefiProtocol.YEARN_VAULTS_V2) {
    return 'yearn.finance Vaults v2';
  }
  return defiProtocol;
});

const css = useCssModule();
</script>

<template>
  <div
    class="d-flex flex-row align-center"
    :class="mode === 'icon' ? 'justify-center' : null"
  >
    <VTooltip top :disabled="mode !== 'icon'" open-delay="300ms">
      <template #activator="{ on, attrs }">
        <VImg
          v-if="mode === 'icon' || mode === 'both'"
          contain
          v-bind="attrs"
          max-width="32px"
          max-height="32px"
          :class="{
            'mr-2': mode !== 'icon',
            [css.icon]: true
          }"
          :src="`./assets/images/protocols/${icon}.svg`"
          v-on="on"
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
    </VTooltip>
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
