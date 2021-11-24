import { BigNumber } from '@rotki/common';

export function setupFormatter() {
  if (process.env.NODE_ENV !== 'development') {
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
