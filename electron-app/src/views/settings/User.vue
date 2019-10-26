<template>
  <div id="settings-user"></div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { create_or_reload_usersettings } from '@/legacy/user_settings';

@Component({})
export default class User extends Vue {
  mounted() {
    create_or_reload_usersettings();
  }
}
</script>

<style scoped></style>
