<script setup lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';

defineProps({
  loading: {
    required: true,
    type: Boolean
  }
});

const emit = defineEmits(['reset']);

const resetSelection = ref<DefiProtocol[]>([]);
const premium = usePremium();
const AAVE = DefiProtocol.AAVE;
const YEARN_VAULTS = DefiProtocol.YEARN_VAULTS;
const YEARN_VAULTS_V2 = DefiProtocol.YEARN_VAULTS_V2;

const { t } = useI18n();

const reset = () => {
  emit('reset', get(resetSelection));
};
</script>

<template>
  <ConfirmableReset
    v-if="premium"
    :loading="loading"
    :tooltip="t('lending.reset_tooltip')"
    :disabled="resetSelection.length === 0"
    @reset="reset()"
  >
    {{ t('lending.reset_confirm') }}
    <div />
    <VRow>
      <VCol class="text-center font-weight-medium">
        {{ t('lending.reset.protocol_selection') }}
      </VCol>
    </VRow>
    <VRow align="center" justify="center">
      <VCol cols="auto">
        <VBtnToggle v-model="resetSelection" multiple>
          <VBtn icon :value="AAVE">
            <DefiProtocolIcon mode="icon" :protocol="AAVE" />
          </VBtn>
          <VBtn icon :value="YEARN_VAULTS">
            <DefiProtocolIcon mode="icon" :protocol="YEARN_VAULTS" />
          </VBtn>
          <VBtn icon :value="YEARN_VAULTS_V2">
            <DefiProtocolIcon mode="icon" :protocol="YEARN_VAULTS_V2" />
          </VBtn>
        </VBtnToggle>
      </VCol>
    </VRow>
  </ConfirmableReset>
</template>
