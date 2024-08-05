import {
  type App as DevtoolsApp,
  setupDevtoolsPlugin,
} from '@vue/devtools-api';
import { BigNumber } from '@rotki/common';

const stateType = 'BigNumber';
const componentStateTypes: string[] = [stateType];

export function registerDevtools(app: DevtoolsApp): void {
  setupDevtoolsPlugin(
    {
      id: 'com.rotki',
      label: 'rotki',
      logo: 'https://raw.githubusercontent.com/rotki/data/main/assets/icons/app_logo.png',
      packageName: 'rotki',
      homepage: 'https://rotki.com',
      componentStateTypes,
      app,
    },
    (api) => {
      api.on.inspectComponent((payload) => {
        if (!payload.instanceData)
          return;

        const bgnState = payload.instanceData.state.filter(state => state.value instanceof BigNumber);

        bgnState.forEach((state) => {
          payload.instanceData.state.push({
            ...state,
            type: stateType,
            editable: false,
            value: {
              _custom: {
                type: BigNumber,
                readonly: true,
                display: state.value.toString(),
                value: state.value,
              },
            },
          });
        });
      });
    },
  );
}
