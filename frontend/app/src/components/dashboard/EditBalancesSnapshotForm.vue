<template>
  <v-form :value="value" class="pt-4" @input="input">
    <div class="mb-2">
      <balance-type-input
        :value="form.category"
        outlined
        :label="$t('dashboard.snapshot.edit.dialog.balances.headers.category')"
        :rules="categoryRules"
        @input="updateForm({ category: $event })"
      />
    </div>
    <div class="mb-n2">
      <div class="text--secondary text-caption mb-2">
        {{ $t('dashboard.snapshot.edit.dialog.balances.headers.asset') }}
      </div>
      <div>
        <v-radio-group v-model="assetType" row>
          <v-radio
            :label="$t('dashboard.snapshot.edit.dialog.balances.token')"
            value="token"
          />
          <v-radio
            :label="$t('dashboard.snapshot.edit.dialog.balances.nft')"
            value="nft"
          />
        </v-radio-group>
      </div>
      <asset-select
        v-if="assetType === 'token'"
        :value="form.assetIdentifier"
        outlined
        :excludes="excludedAssets"
        :show-ignored="true"
        :label="$t('dashboard.snapshot.edit.dialog.balances.headers.asset')"
        :enable-association="false"
        :rules="assetRules"
        @input="updateForm({ assetIdentifier: $event })"
      />
      <v-text-field
        v-if="assetType === 'nft'"
        :value="form.assetIdentifier"
        :label="$t('dashboard.snapshot.edit.dialog.balances.headers.asset')"
        outlined
        :rules="assetRules"
        :hint="$t('dashboard.snapshot.edit.dialog.balances.nft_hint')"
        @input="updateForm({ assetIdentifier: $event })"
      />
    </div>
    <div class="mb-4">
      <amount-input
        :disabled="assetType === 'nft'"
        :value="form.amount"
        outlined
        :label="$t('dashboard.snapshot.edit.dialog.balances.headers.amount')"
        :rules="amountRules"
        @input="updateForm({ amount: $event })"
      />
    </div>
    <div class="mb-4">
      <amount-input
        :value="form.usdValue"
        outlined
        :label="
          $t('dashboard.snapshot.edit.dialog.balances.headers.value', {
            currency: currencySymbol
          })
        "
        :rules="valueRules"
        @input="updateForm({ usdValue: $event })"
      />
    </div>
  </v-form>
</template>
<script lang="ts">
import {
  defineComponent,
  onBeforeMount,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import BalanceTypeInput from '@/components/inputs/BalanceTypeInput.vue';
import { setupGeneralSettings } from '@/composables/session';
import i18n from '@/i18n';
import { BalanceSnapshotPayload } from '@/store/balances/types';
import { isNft } from '@/utils/nft';

export default defineComponent({
  name: 'EditBalancesSnapshotForm',
  components: { BalanceTypeInput },
  props: {
    value: {
      required: false,
      type: Boolean,
      default: false
    },
    form: { required: true, type: Object as PropType<BalanceSnapshotPayload> },
    excludedAssets: {
      required: false,
      type: Array as PropType<string[]>,
      default: () => []
    }
  },
  emits: ['update:form', 'input'],
  setup(props, { emit }) {
    const { form, excludedAssets } = toRefs(props);
    const { currencySymbol } = setupGeneralSettings();

    const assetType = ref<string>('token');

    const input = (valid: boolean) => {
      emit('input', valid);
    };

    const updateForm = (partial: Partial<BalanceSnapshotPayload>) => {
      emit('update:form', {
        ...(get(form) as BalanceSnapshotPayload),
        ...partial
      });
    };

    const checkAssetType = () => {
      const formVal = get(form);
      if (isNft(formVal.assetIdentifier)) {
        set(assetType, 'nft');
      }
    };

    onBeforeMount(() => {
      checkAssetType();
    });

    watch(form, () => {
      checkAssetType();
    });

    watch(assetType, assetType => {
      if (assetType === 'nft') {
        updateForm({ amount: '1' });
      }
    });

    const categoryRules = [
      (v: string) =>
        !!v ||
        i18n
          .t('dashboard.snapshot.edit.dialog.balances.rules.category')
          .toString()
    ];
    const assetRules = [
      (v: string) =>
        !!v ||
        i18n
          .t('dashboard.snapshot.edit.dialog.balances.rules.asset')
          .toString(),
      (v: string) =>
        !get(excludedAssets).includes(v) ||
        i18n
          .t(
            'dashboard.snapshot.edit.dialog.balances.rules.asset_non_duplicate'
          )
          .toString()
    ];
    const amountRules = [
      (v: string) =>
        !!v ||
        i18n
          .t('dashboard.snapshot.edit.dialog.balances.rules.amount')
          .toString()
    ];
    const valueRules = [
      (v: string) =>
        !!v ||
        i18n.t('dashboard.snapshot.edit.dialog.balances.rules.value').toString()
    ];

    return {
      assetType,
      currencySymbol,
      categoryRules,
      assetRules,
      amountRules,
      valueRules,
      input,
      updateForm
    };
  }
});
</script>
