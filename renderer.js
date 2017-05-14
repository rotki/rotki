const zerorpc = require("zerorpc");
let client = new zerorpc.Client();


client.connect("tcp://127.0.0.1:4242");


var body = $("body");
body.addClass("loading");

function create_box(id, icon, number, text) {
    var str = '<div class="panel panel-primary"><div class="panel-heading" id="'+id+'"><div class="row"><div class="col-xs-3"><i class="fa '+icon +' fa-5x"></i></div><div class="col-xs-9 text-right"><div class="huge">'+number+'</div><div id="status_box_text">'+text+'</div></div></div></div><a href="#"><div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span><div class="clearfix"></div></div></a></div>';
    return $(str);
}


client.invoke("echo", "server ready", (error, res) => {
    if(error || res !== 'server ready') {
	var loading_wrapper = document.querySelector('.loadingwrapper');
	var loading_wrapper_text = document.querySelector('.loadingwrapper_text');
	console.log("Response was: " + res);
	console.error(error);
	loading_wrapper.style.background = "rgba( 255, 255, 255, .8 ) 50% 50% no-repeat";
	loading_wrapper_text.textContent = "ERROR: Failed to connect to the backend. Check Log";
  } else {
      body.removeClass("loading");
      console.log("server is ready");
  }
});


var str = '<div class="panel panel-primary"><div class="panel-heading" id="status_box"><div class="row"><div class="col-xs-3"><i class="fa fa-plug fa-5x"></i></div><div class="col-xs-9 text-right"><div class="huge">26</div><div id="status_box_text">AAAAA</div></div></div></div><a href="#"><div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span><div class="clearfix"></div></div></a></div>';

a = create_box("status_box", "fa-plug", "1", "TEXT1");
a.appendTo($('#leftest-column'));
create_box("status_box", "fa-money", "2", "TEXT2").appendTo($('#leftest-column'));




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
