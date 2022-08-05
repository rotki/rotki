import { BigNumber } from '@rotki/common';
import { reactive, toRefs } from '@vue/composition-api';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { getBnFormat } from '@/data/amount_formatter';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { ActionStatus } from '@/store/types';
import {
  FrontendSettings,
  FrontendSettingsPayload
} from '@/types/frontend-settings';
import { assert } from '@/utils/assertions';

export const useFrontendSettingsStore = defineStore('settings/frontend', () => {
  const frontendSettings = reactive(FrontendSettings.parse({}));

  async function updateSetting(
    payload: FrontendSettingsPayload
  ): Promise<ActionStatus> {
    const props = Object.keys(payload);
    assert(props.length > 0, 'Payload must be not-empty');
    try {
      const updatedSettings = { ...frontendSettings, ...payload };
      const { other } = await api.setSettings({
        frontendSettings: JSON.stringify(
          axiosSnakeCaseTransformer(updatedSettings)
        )
      });

      Object.assign(frontendSettings, updatedSettings);

      if (payload.thousandSeparator || payload.decimalSeparator) {
        BigNumber.config({
          FORMAT: getBnFormat(
            other.frontendSettings.thousandSeparator,
            other.frontendSettings.decimalSeparator
          )
        });
      }

      return {
        success: true
      };
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  }

  const update = (settings: FrontendSettings) => {
    Object.assign(frontendSettings, settings);
  };

  const reset = () => {
    Object.assign(frontendSettings, FrontendSettings.parse({}));
  };

  return {
    ...toRefs(frontendSettings),
    updateSetting,
    update,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useFrontendSettingsStore, import.meta.hot)
  );
}
