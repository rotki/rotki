<script setup lang="ts">
import type { EthereumValidator } from '@/types/blockchain/accounts';
import { useEthValidatorUtils } from '@/composables/staking/eth/use-eth-validator-utils';
import HashLink from '@/modules/common/links/HashLink.vue';

interface Props {
  validator: EthereumValidator;
}

defineProps<Props>();

const { t } = useI18n({ useScope: 'global' });
const { getColor } = useEthValidatorUtils();
</script>

<template>
  <RuiChip
    size="sm"
    :color="getColor(validator.status)"
    content-class="text-xs inline-flex gap-1 items-center"
    class="uppercase font-semibold"
  >
    {{ validator.status }}

    <template v-if="validator.consolidatedInto">
      <RuiTooltip
        persist-on-tooltip-hover
        :open-delay="300"
      >
        <template #activator>
          <RuiIcon
            name="lu-merge"
            size="16"
            class="bg-rui-grey-200 text-rui-grey-800 rounded-full p-0.5 -mr-1.5 cursor-pointer"
          />
        </template>
        <div>{{ t('blockchain_balances.validators.consolidated') }}</div>
        <HashLink
          location="eth2"
          :text="validator.consolidatedInto.toString()"
        />
      </RuiTooltip>
    </template>
  </RuiChip>
</template>
