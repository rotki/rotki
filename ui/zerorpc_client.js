const zerorpc = require("zerorpc");
// max timeout is now 120 seconds
let client = new zerorpc.Client({timeout:120, heartbeatInterval: 15000});

module.exports = function () {
    this.client = client;
};
