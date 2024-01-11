import { HttpResponse, http } from 'msw';
import historyTypeMappings from '../../fixtures/history-type-mappings.json';

const backendUrl = process.env.VITE_BACKEND_URL;

export default [
  http.get(`${backendUrl}/api/1/history/events/type_mappings`, () =>
    HttpResponse.json(historyTypeMappings, { status: 200 })
  )
];
