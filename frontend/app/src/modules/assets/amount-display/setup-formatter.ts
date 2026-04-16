import { BigNumber } from '@rotki/common';
import { checkIfDevelopment } from '@shared/utils';

export function setupFormatter(): void {
  if (!checkIfDevelopment())
    return;

  const formatter: {
    hasBody: () => boolean;
    header: (obj: any) => unknown[] | null;
  } = {
    hasBody: (): boolean => false,
    header: (obj: any): unknown[] | null => {
      if (!(obj instanceof BigNumber))
        return null;

      return ['div', {}, obj.toString()];
    },
  };
  // @ts-expect-error object does not exist in window
  window.devtoolsFormatters = [formatter];
}
