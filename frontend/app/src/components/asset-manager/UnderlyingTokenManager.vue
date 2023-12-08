<script setup lang="ts">
import { EvmTokenKind, type UnderlyingToken } from '@rotki/common/lib/data';
import useVuelidate from '@vuelidate/core';
import { between, helpers, numeric, required } from '@vuelidate/validators';
import { evmTokenKindsData } from '@/types/blockchain/chains';
import { toMessages } from '@/utils/validation';

const props = defineProps<{ value: UnderlyingToken[] }>();

const emit = defineEmits<{ (e: 'input', value: UnderlyingToken[]): void }>();
const { t } = useI18n();

const { value } = toRefs(props);

const input = (value: UnderlyingToken[]) => emit('input', value);

const underlyingAddress = ref<string>('');
const tokenKind = ref<EvmTokenKind>(EvmTokenKind.ERC20);
const underlyingWeight = ref<string>('');
const form = ref<any>(null);

const rules = {
  address: {
    required: helpers.withMessage(
      t('underlying_token_manager.validation.address_non_empty'),
      required
    ),
    isValidEthAddress: helpers.withMessage(
      t('underlying_token_manager.validation.valid'),
      isValidEthAddress
    )
  },
  weight: {
    required: helpers.withMessage(
      t('underlying_token_manager.validation.non_empty'),
      required
    ),
    notNaN: helpers.withMessage(
      t('underlying_token_manager.validation.not_valid'),
      numeric
    ),
    minMax: helpers.withMessage(
      t('underlying_token_manager.validation.out_of_range'),
      between(1, 100)
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    address: underlyingAddress,
    weight: underlyingWeight
  },
  { $autoDirty: true, $stopPropagation: true }
);

const addToken = () => {
  const underlyingTokens = [...get(value)];
  const index = underlyingTokens.findIndex(
    ({ address }) => address === get(underlyingAddress)
  );

  const token = {
    address: get(underlyingAddress),
    tokenKind: get(tokenKind),
    weight: get(underlyingWeight)
  };

  if (index >= 0) {
    underlyingTokens[index] = token;
  } else {
    underlyingTokens.push(token);
  }

  (get(form) as any)?.reset();
  get(v$).$reset();
  input(underlyingTokens);
};

const editToken = (token: UnderlyingToken) => {
  set(underlyingAddress, token.address);
  set(tokenKind, token.tokenKind);
  set(underlyingWeight, token.weight);
  deleteToken(token.address);
};

const deleteToken = (address: string) => {
  const underlyingTokens = [...get(value)];
  input(
    underlyingTokens.filter(
      ({ address: tokenAddress }) => tokenAddress !== address
    )
  );
};
</script>

<template>
  <VForm ref="form" :value="!v$.$invalid">
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
        <VSelect
          v-model="tokenKind"
          outlined
          :label="t('asset_form.labels.token_kind')"
          :items="evmTokenKindsData"
          item-text="label"
          item-value="identifier"
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
          :hint="t('underlying_token_manager.hint')"
          :label="t('underlying_token_manager.labels.weight')"
        >
          <template #append-outer>
            <RuiButton
              variant="text"
              color="primary"
              icon
              :disabled="v$.$invalid"
              class="mt-n2"
              @click="addToken()"
            >
              <RuiIcon name="add-line" />
            </RuiButton>
          </template>
        </RuiTextField>
      </div>
    </div>
    <RuiCard class="underlying-tokens">
      <VSimpleTable fixed-header height="200px">
        <thead>
          <tr>
            <th>{{ t('common.address') }}</th>
            <th>{{ t('underlying_token_manager.tokens.token_kind') }}</th>
            <th>{{ t('underlying_token_manager.tokens.weight') }}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-for="token in value" :key="token.address">
            <td class="grow">{{ token.address }}</td>
            <td class="shrink">{{ token.tokenKind.toUpperCase() }}</td>
            <td class="shrink text-no-wrap">
              {{
                t('underlying_token_manager.tokens.weight_percentage', {
                  weight: token.weight
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
      </VSimpleTable>
    </RuiCard>
  </VForm>
</template>
