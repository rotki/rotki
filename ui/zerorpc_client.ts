const zerorpc = require("zerorpc");
// max timeout is now 9999 seconds
let client = new zerorpc.Client({timeout:9999, heartbeatInterval: 15000});

module.exports = function () {
    this.client = client;
};
