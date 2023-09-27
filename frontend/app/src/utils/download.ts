import { type AxiosResponse } from 'axios';

export const downloadFileByUrl = (url: string, fileName: string): void => {
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', fileName);
  if (document.createEvent) {
    const event = document.createEvent('MouseEvents');
    event.initEvent('click', true, true);
    link.dispatchEvent(event);
  } else {
    link.click();
  }
};

export const downloadFileByBlobResponse = (
  response: AxiosResponse,
  filename: string
) => {
  const url = window.URL.createObjectURL(response.request.response);
  downloadFileByUrl(url, filename);
};

export const downloadFileByTextContent = (
  text: string,
  filename: string,
  type: 'plain' | 'json' | 'csv' = 'plain'
) => {
  const file = new Blob([text], {
    type: `text/${type}`
  });
  const url = window.URL.createObjectURL(file);
  downloadFileByUrl(url, filename);
};
