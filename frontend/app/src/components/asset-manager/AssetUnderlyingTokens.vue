<script setup lang="ts">
import { type SupportedAsset } from '@rotki/common/lib/data';

defineProps<{
  cols: number;
  asset: SupportedAsset;
}>();

const { t } = useI18n();
</script>

<template>
  <TableExpandContainer visible :colspan="cols" no-padding>
    <template #title>
      {{ t('asset_table.underlying_tokens') }}
    </template>
    <VSimpleTable>
      <thead>
        <tr>
          <th>{{ t('common.address') }}</th>
          <th>{{ t('underlying_token_manager.tokens.token_kind') }}</th>
          <th>{{ t('underlying_token_manager.tokens.weight') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="token in asset.underlyingTokens" :key="token.address">
          <td class="grow">
            <HashLink :text="token.address" full-address />
          </td>
          <td class="shrink">{{ token.tokenKind.toUpperCase() }}</td>
          <td class="shrink">
            {{
              t('underlying_token_manager.tokens.weight_percentage', {
                weight: token.weight
              })
            }}
          </td>
        </tr>
      </tbody>
    </VSimpleTable>
  </TableExpandContainer>
</template>
