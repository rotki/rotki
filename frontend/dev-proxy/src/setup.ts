import { Application } from 'express';

export function enableCors(server: Application): void {
  server.use(function (req, res, next) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader(
      'Access-Control-Allow-Methods',
      'GET, POST, OPTIONS, PUT, PATCH, DELETE'
    );
    res.setHeader(
      'Access-Control-Allow-Headers',
      'X-Requested-With,content-type'
    );
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    next();
  });
}
