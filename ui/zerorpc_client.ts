const zerorpc = require('zerorpc');
// max timeout is now 9999 seconds
const client = new zerorpc.Client({timeout: 9999, heartbeatInterval: 15000});

export default client;
