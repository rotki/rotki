<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
import { isNft } from '@/utils/nft';
import { usePropVModel } from '@/utils/model';
import type { BigNumber } from '@rotki/common';
import type { BalanceSnapshotPayload } from '@/types/snapshots';
import type EditBalancesSnapshotAssetPriceForm
  from './EditBalancesSnapshotAssetPriceForm.vue';

interface BalanceSnapshotPayloadAndLocation extends BalanceSnapshotPayload {
  location: string;
}

const props = withDefaults(
  defineProps<{
    edit?: boolean;
    form: BalanceSnapshotPayloadAndLocation;
    locations?: string[];
    previewLocationBalance?: Record<string, BigNumber> | null;
    timestamp: number;
  }>(),
  {
    edit: false,
    locations: () => [],
    previewLocationBalance: null,
  },
);

const emit = defineEmits<{
  (e: 'update:form', data: BalanceSnapshotPayloadAndLocation): void;
  (e: 'update:asset', asset: string): void;
}>();

const { form } = toRefs(props);

const category = usePropVModel(props, 'form', 'category', emit);
const assetIdentifier = usePropVModel(props, 'form', 'assetIdentifier', emit);
const amount = usePropVModel(props, 'form', 'amount', emit);
const usdValue = usePropVModel(props, 'form', 'usdValue', emit);
const location = usePropVModel(props, 'form', 'location', emit);

const { t } = useI18n();

const assetType = ref<string>('token');
const assetPriceForm = ref<InstanceType<typeof EditBalancesSnapshotAssetPriceForm>>();

const rules = {
  category: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.balances.rules.category'), required),
  },
};

const { setValidation } = useEditBalancesSnapshotForm();

const v$ = setValidation(
  rules,
  {
    category,
  },
  {
    $autoDirty: true,
  },
);

function updateAsset(asset: string) {
  emit('update:asset', asset);
}

function checkAssetType() {
  if (isNft(get(assetIdentifier)))
    set(assetType, 'nft');
}

function submitPrice() {
  const form = get(assetPriceForm);
  if (form)
    form.submitPrice();
}

watch(assetType, (assetType) => {
  if (assetType === 'nft')
    set(amount, '1');
});

watchImmediate(form, () => {
  checkAssetType();
});

defineExpose({
  submitPrice,
});
</script>

<template>
  <form class="flex flex-col gap-2">
    <BalanceTypeInput
      v-model="category"
      :label="t('common.category')"
      :error-messages="toMessages(v$.category)"
    />
    <div>
      <div class="text-rui-text-secondary text-caption">
        {{ t('common.asset') }}
      </div>
      <div>
        <RuiRadioGroup
          v-model="assetType"
          color="primary"
          inline
          :disabled="edit"
        >
          <RuiRadio
            :label="t('dashboard.snapshot.edit.dialog.balances.token')"
            value="token"
          />
          <RuiRadio
            :label="t('dashboard.snapshot.edit.dialog.balances.nft')"
            value="nft"
          />
        </RuiRadioGroup>
      </div>
    </div>

    <EditBalancesSnapshotAssetPriceForm
      ref="assetPriceForm"
      v-model:asset="assetIdentifier"
      v-model:amount="amount"
      v-model:usd-value="usdValue"
      :timestamp="timestamp"
      :disable-asset="edit"
      :nft="assetType === 'nft'"
      @update:asset="updateAsset($event)"
    />

    <EditBalancesSnapshotLocationSelector
      v-model="location"
      optional-show-existing
      :locations="locations"
      :preview-location-balance="previewLocationBalance"
    />
  </form>
</template>
