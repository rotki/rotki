<script setup lang="ts">
import ExternalLink from '@/components/helper/ExternalLink.vue';
import { useEthStaking } from '@/composables/blockchain/accounts/staking';

const { t } = useI18n({ useScope: 'global' });
const { validatorsLimitInfo } = useEthStaking();
</script>

<template>
  <RuiTooltip
    v-if="validatorsLimitInfo.showWarning"
    :open-delay="300"
    persist-on-tooltip-hover
    tooltip-class="max-w-[12rem]"
  >
    <template #activator>
      <RuiIcon
        size="24"
        class="text-rui-text-secondary p-0.5 cursor-pointer"
        name="lu-circle-alert"
      />
    </template>

    <i18n-t
      scope="global"
      keypath="eth2_validator_limit_row.complete"
      tag="div"
    >
      <template #limit>
        {{ validatorsLimitInfo.limit }}
      </template>
      <template #total>
        {{ validatorsLimitInfo.total }}
      </template>
      <template #button>
        <ExternalLink
          class="!text-white !leading-[0]"
          :text="t('common.here')"
          premium
        />
      </template>
    </i18n-t>
  </RuiTooltip>
</template>
