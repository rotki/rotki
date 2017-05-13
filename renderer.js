const zerorpc = require("zerorpc");
let client = new zerorpc.Client();


client.connect("tcp://127.0.0.1:4242");
var status_box_text = document.querySelector('#status_box_text');
var status_box = document.querySelector('#status_box');
status_box_text.textContent = "Initializing backend";


client.invoke("echo", "server ready", (error, res) => {
    if(error || res !== 'server ready') {
	console.log("Response was: " + res);
	console.error(error);
	status_box_text.textContent = "Failed to connect to the backend. Check Log";
	status_box.style.backgroundColor = "red";
  } else {
      console.log("server is ready");
      status_box_text.textContent = "Connected to the Backend.";
      status_box.style.backgroundColor = "green";
  }
});


// let result = document.querySelector('#result');
// formula.addEventListener('input', () => {
//   client.invoke("calc", formula.value, (error, res) => {
//     if(error) {
// 	console.error(error);
//     } else {
// 	result.textContent = res;
//     }
//   });
// });

// formula.dispatchEvent(new Event('input'));
