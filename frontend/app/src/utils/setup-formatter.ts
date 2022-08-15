import { BigNumber } from '@rotki/common';
import { checkIfDevelopment } from '@/utils/env-utils';

export function setupFormatter() {
  if (!checkIfDevelopment()) {
    return;
  }
  // @ts-ignore
  window.devtoolsFormatters = [
    {
      header: function (obj: any) {
        if (!(obj instanceof BigNumber)) {
          return null;
        }
        return ['div', {}, obj.toString()];
      },
      hasBody: function () {
        return false;
      }
    }
  ];
}
