<template>
  <v-row>
    <v-col>
      <div :class="$style.identifier">
        <slot />
      </div>
      <div class="loan-header__owner secondary--text text--lighten-2">
        {{ $t('loan_header.owned_by') }}
        <hash-link :text="owner" class="d-inline font-weight-medium" />
      </div>
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import HashLink from '@/components/helper/HashLink.vue';

export default defineComponent({
  name: 'LoanHeader',
  components: { HashLink },
  props: {
    owner: {
      required: true,
      type: String
    }
  }
});
</script>

<style lang="scss" module>
.identifier {
  font-size: 24px;
  font-weight: bold;
}
</style>
