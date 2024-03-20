import { BigNumber } from '@rotki/common';

export function setupFormatter(): void {
  if (!checkIfDevelopment())
    return;

  // @ts-expect-error object does not exist in window
  window.devtoolsFormatters = [
    {
      header: (obj: any): unknown[] | null => {
        if (!(obj instanceof BigNumber))
          return null;

        return ['div', {}, obj.toString()];
      },
      hasBody: (): boolean => false,
    },
  ];
}
