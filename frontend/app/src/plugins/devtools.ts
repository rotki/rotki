import type { App } from 'vue';
import { BigNumber } from '@rotki/common';
import { setupDevtoolsPlugin } from '@vue/devtools-api';

const stateType = 'BigNumber';
const componentStateTypes: string[] = [stateType];

export function registerDevtools(app: App): void {
  setupDevtoolsPlugin(
    {
      app,
      componentStateTypes,
      homepage: 'https://rotki.com',
      id: 'com.rotki',
      label: 'rotki',
      logo: 'https://raw.githubusercontent.com/rotki/data/main/assets/icons/app_logo.png',
      packageName: 'rotki',
    },
    (api) => {
      api.on.inspectComponent((payload) => {
        if (!payload.instanceData)
          return;

        const bgnState = payload.instanceData.state.filter(state => state.value instanceof BigNumber);

        bgnState.forEach((state) => {
          payload.instanceData.state.push({
            ...state,
            editable: false,
            type: stateType,
            value: {
              _custom: {
                display: state.value.toString(),
                readonly: true,
                type: BigNumber,
                value: state.value,
              },
            },
          });
        });
      });
    },
  );
}
