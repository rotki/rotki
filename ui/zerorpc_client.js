const zerorpc = require("zerorpc");
// max timeout is now 30 seconds
let client = new zerorpc.Client({timeout:30, heartbeatInterval: 15000});

module.exports = function () {
    this.client = client;
};
