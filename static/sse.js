window.onload = function(){

    var eventSource = new EventSource("/success");

    eventSource.onmessage = function(e) {
        console.log(e.data);
    };

};