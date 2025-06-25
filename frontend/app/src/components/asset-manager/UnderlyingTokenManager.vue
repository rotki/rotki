<script setup lang="ts">
import SimpleTable from '@/components/common/SimpleTable.vue';
import RowActions from '@/components/helper/RowActions.vue';
import { evmTokenKindsData } from '@/types/blockchain/chains';
import { toMessages } from '@/utils/validation';
import { isValidEthAddress, TokenKind, type UnderlyingToken } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { between, helpers, numeric, required } from '@vuelidate/validators';

const modelValue = defineModel<UnderlyingToken[]>({ required: true });

const { t } = useI18n({ useScope: 'global' });

const underlyingAddress = ref<string>('');
const tokenKind = ref<TokenKind>(TokenKind.ERC20);
const underlyingWeight = ref<string>('');

const rules = {
  address: {
    isValidEthAddress: helpers.withMessage(t('underlying_token_manager.validation.valid'), isValidEthAddress),
    required: helpers.withMessage(t('underlying_token_manager.validation.address_non_empty'), required),
  },
  weight: {
    minMax: helpers.withMessage(t('underlying_token_manager.validation.out_of_range'), between(1, 100)),
    notNaN: helpers.withMessage(t('underlying_token_manager.validation.not_valid'), numeric),
    required: helpers.withMessage(t('underlying_token_manager.validation.non_empty'), required),
  },
};

const v$ = useVuelidate(
  rules,
  {
    address: underlyingAddress,
    weight: underlyingWeight,
  },
  { $autoDirty: true, $stopPropagation: true },
);

function addToken() {
  const underlyingTokens = [...get(modelValue)];
  const index = underlyingTokens.findIndex(({ address }) => address === get(underlyingAddress));

  const token = {
    address: get(underlyingAddress),
    tokenKind: get(tokenKind),
    weight: get(underlyingWeight),
  };

  if (index >= 0)
    underlyingTokens[index] = token;
  else underlyingTokens.push(token);

  resetForm();
  get(v$).$reset();
  set(modelValue, underlyingTokens);
}

function editToken(token: UnderlyingToken) {
  set(underlyingAddress, token.address);
  set(tokenKind, token.tokenKind);
  set(underlyingWeight, token.weight);
  deleteToken(token.address);
}

function deleteToken(address: string) {
  const underlyingTokens = [...get(modelValue)];
  set(
    modelValue,
    underlyingTokens.filter(({ address: tokenAddress }) => tokenAddress !== address),
  );
}

function resetForm() {
  set(underlyingAddress, '');
  set(underlyingWeight, '');
  set(tokenKind, TokenKind.ERC20);
}
</script>

<template>
  <form class="flex flex-col gap-4">
    <div class="text-h6">
      {{ t('underlying_token_manager.labels.tokens') }}
    </div>

    <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-2 my-2">
      <div class="md:col-span-2">
        <RuiTextField
          v-model="underlyingAddress"
          :error-messages="toMessages(v$.address)"
          variant="outlined"
          color="primary"
          :label="t('common.address')"
        />
      </div>

      <div class="col-span-1">
        <RuiMenuSelect
          v-model="tokenKind"
          :label="t('asset_form.labels.token_kind')"
          :options="evmTokenKindsData"
          key-attr="identifier"
          text-attr="label"
          variant="outlined"
        />
      </div>

      <div class="col-span-1">
        <RuiTextField
          v-model="underlyingWeight"
          variant="outlined"
          color="primary"
          type="number"
          max="100"
          min="1"
          :error-messages="toMessages(v$.weight)"
          :label="t('underlying_token_manager.labels.weight')"
        >
          <template #append>
            <RuiTooltip
              :popper="{ placement: 'top' }"
              :open-delay="400"
            >
              <template #activator>
                <RuiButton
                  type="button"
                  variant="text"
                  icon
                  size="sm"
                >
                  <RuiIcon
                    :size="20"
                    name="lu-circle-help"
                  />
                </RuiButton>
              </template>
              {{ t('underlying_token_manager.hint') }}
            </RuiTooltip>
          </template>
        </RuiTextField>
      </div>

      <RuiButton
        color="primary"
        class="col-span-2 lg:col-span-4"
        :disabled="v$.$invalid"
        @click="addToken()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('common.actions.add') }}
      </RuiButton>
    </div>

    <SimpleTable class="underlying-tokens min-h-24">
      <thead>
        <tr>
          <th scope="col">
            {{ t('common.address') }}
          </th>
          <th scope="col">
            {{ t('underlying_token_manager.tokens.token_kind') }}
          </th>
          <th scope="col">
            {{ t('underlying_token_manager.tokens.weight') }}
          </th>
          <th scope="col" />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="token in modelValue"
          :key="token.address"
        >
          <td class="grow">
            {{ token.address }}
          </td>
          <td class="shrink">
            {{ token.tokenKind.toUpperCase() }}
          </td>
          <td class="shrink text-no-wrap">
            {{
              t('underlying_token_manager.tokens.weight_percentage', {
                weight: token.weight,
              })
            }}
          </td>
          <td>
            <RowActions
              :edit-tooltip="t('underlying_token_manager.edit_tooltip')"
              :delete-tooltip="t('underlying_token_manager.delete_tooltip')"
              @delete-click="deleteToken(token.address)"
              @edit-click="editToken(token)"
            />
          </td>
        </tr>
      </tbody>
    </SimpleTable>
  </form>
</template>
