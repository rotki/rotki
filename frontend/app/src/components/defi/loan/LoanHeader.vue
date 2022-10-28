<template>
  <v-row>
    <v-col>
      <div :class="$style.identifier">
        <slot />
      </div>
      <div class="loan-header__owner secondary--text text--lighten-2">
        {{ t('loan_header.owned_by') }}
        <hash-link :text="owner" class="d-inline font-weight-medium" />
      </div>
    </v-col>
  </v-row>
</template>
<script setup lang="ts">
import HashLink from '@/components/helper/HashLink.vue';

defineProps({
  owner: {
    required: true,
    type: String
  }
});

const { t } = useI18n();
</script>

<style lang="scss" module>
.identifier {
  font-size: 24px;
  font-weight: bold;
}
</style>
