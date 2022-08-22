<template>
  <v-navigation-drawer
    width="400px"
    class="user-notes-sidebar"
    :class="$vuetify.breakpoint.smAndDown ? 'user-notes-sidebar--mobile' : null"
    absolute
    clipped
    :value="visible"
    right
    temporary
    hide-overlay
    @input="visibleUpdate($event)"
  >
    <v-sheet elevation="2">
      <v-row no-gutters justify="space-between" align="center">
        <v-col>
          <v-tabs
            v-model="tab"
            class="tabs"
            fixed-tabs
            height="42"
            mobile-breakpoint="0"
          >
            <v-tab>
              {{ $t('notes_menu.tabs.general') }}
            </v-tab>
            <v-tab v-if="locationName" class="ml-2">
              {{ $t('notes_menu.tabs.in_this_page', { page: locationName }) }}
            </v-tab>
          </v-tabs>
        </v-col>
        <v-col cols="auto" class="pr-2">
          <v-btn icon @click="visibleUpdate(false)">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-col>
      </v-row>
    </v-sheet>

    <user-notes-list
      :key="location + tab"
      :location="tab === 0 ? '' : location"
    />
  </v-navigation-drawer>
</template>

<script lang="ts">
import { get, set } from '@vueuse/core';
import { computed, defineComponent, ref, watch } from 'vue';
import UserNotesList from '@/components/UserNotesList.vue';
import { useRoute } from '@/composables/common';
import { routesRef } from '@/router/routes';

export default defineComponent({
  name: 'UserNotesSidebar',
  components: { UserNotesList },
  props: {
    visible: { required: true, type: Boolean }
  },
  emits: ['visible:update', 'about'],
  setup(_, { emit }) {
    const tab = ref<number>(0);
    const visibleUpdate = (_visible: boolean) => {
      emit('visible:update', _visible);
    };

    const route = useRoute();

    const location = computed<string>(() => {
      const meta = get(route).meta;
      if (meta && meta.noteLocation) return meta.noteLocation;

      let noteLocation = '';
      get(route).matched.forEach(matched => {
        if (matched.meta.noteLocation) {
          noteLocation = matched.meta.noteLocation;
        }
      });

      return noteLocation;
    });

    const Routes = get(routesRef);
    const locationName = computed<string>(() => {
      // @ts-ignore
      return Routes[get(location)]?.text ?? '';
    });

    watch(locationName, locationName => {
      if (locationName === '') {
        set(tab, 0);
      }
    });

    return {
      tab,
      location,
      locationName,
      visibleUpdate
    };
  }
});
</script>
<style lang="scss" scoped>
.user-notes-sidebar {
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

.tabs {
  ::v-deep {
    .v-slide-group {
      &__prev,
      &__next {
        display: none;
      }

      &__wrapper {
        .v-tab {
          font-size: 0.75rem;
          padding: 0 1rem;
          margin-left: 0;
          flex: none;
          width: auto;
        }
      }
    }
  }
}
</style>
