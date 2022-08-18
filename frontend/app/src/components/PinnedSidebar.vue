<template>
  <v-navigation-drawer
    class="pinned-sidebar"
    clipped
    width="520px"
    :value="visible"
    right
    temporary
    hide-overlay
    @input="visibleUpdate($event)"
  >
    <div>
      <component :is="pinned.name" v-if="pinned" v-bind="pinned.props" />
    </div>
  </v-navigation-drawer>
</template>
<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import ReportActionableCard from '@/components/profitloss/ReportActionableCard.vue';
import { useAreaVisibilityStore } from '@/store/session/visibility';

export default defineComponent({
  name: 'PinnedSidebar',
  components: {
    ReportActionableCard
  },
  props: {
    visible: { required: true, type: Boolean }
  },
  emits: ['visible:update'],
  setup(_, { emit }) {
    const visibleUpdate = (_visible: boolean) => {
      emit('visible:update', _visible);
    };

    const { pinned } = storeToRefs(useAreaVisibilityStore());

    return {
      pinned,
      visibleUpdate
    };
  }
});
</script>

<style scoped lang="scss">
.pinned-sidebar {
  top: 64px !important;
  box-shadow: 0 2px 12px rgba(74, 91, 120, 0.1);
  padding-top: 0 !important;
  border-top: var(--v-rotki-light-grey-darken1) solid thin;

  &--mobile {
    top: 56px !important;
  }

  &.v-navigation-drawer {
    &--is-mobile {
      padding-top: 0 !important;
    }
  }
}
</style>
