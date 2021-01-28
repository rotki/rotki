import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapState } from 'vuex';
import { ActionStatus } from '@/store/types';
import { GeneralSettings, SettingsUpdate } from '@/typing/types';

@Component({
  computed: {
    ...mapState('session', ['generalSettings'])
  },
  methods: {
    ...mapActions('session', ['settingsUpdate'])
  }
})
export default class SettingsMixin extends Vue {
  settingsUpdate!: (update: SettingsUpdate) => Promise<ActionStatus>;
  generalSettings!: GeneralSettings;
}
