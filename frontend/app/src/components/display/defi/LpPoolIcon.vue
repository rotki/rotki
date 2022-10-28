<template>
  <div class="d-flex">
    <div class="d-flex align-center">
      <asset-icon
        circle
        :identifier="assets[0]"
        size="32px"
        padding="0"
        :show-chain="false"
      />
      <asset-icon
        v-if="!multiple"
        circle
        :class="css['second-icon']"
        :identifier="assets[1]"
        size="32px"
        padding="0"
        :show-chain="false"
      />
      <div v-else :class="[css['second-icon'], css['more-assets']]">
        +{{ assets.length - 1 }}
      </div>
    </div>
    <div :class="css['lp-type-icon']">
      <v-avatar
        :size="20"
        color="grey lighten-4"
        :class="css['lp-type-icon-avatar']"
      >
        <v-img :width="16" :height="16" :src="icon" />
      </v-avatar>
    </div>
  </div>
</template>
<script setup lang="ts">
import { LpType } from '@rotki/common/lib/defi';
import { PropType } from 'vue';

const props = defineProps({
  assets: {
    required: true,
    type: Array as PropType<string[]>,
    validator: value => Array.isArray(value) && value.length >= 2
  },
  type: {
    required: true,
    type: String as PropType<LpType>
  }
});

const { assets, type } = toRefs(props);

const data = [
  {
    identifier: LpType.UNISWAP_V2,
    icon: '/assets/images/defi/uniswap.svg'
  },
  {
    identifier: LpType.UNISWAP_V3,
    icon: '/assets/images/defi/uniswap.svg'
  },
  {
    identifier: LpType.SUSHISWAP,
    icon: '/assets/images/modules/sushiswap.svg'
  },
  {
    identifier: LpType.BALANCER,
    icon: '/assets/images/defi/balancer.svg'
  }
];

const icon = computed(() => {
  const selected = data.find(({ identifier }) => identifier === get(type));

  if (!selected) return null;

  return selected.icon;
});

const multiple = computed<boolean>(() => get(assets).length > 2);

const css = useCssModule();
</script>

<style module lang="scss">
.second-icon {
  z-index: 0;
  margin-left: -10px;
}

.more-assets {
  border-radius: 50%;
  font-size: 1rem;
  width: 32px;
  height: 32px;
  background: var(--v-graphFade-darken4);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
}

.lp-type-icon {
  margin-left: -12px;
  margin-top: -12px;
}

.lp-type-icon-avatar {
  padding: 2px;
}
</style>
