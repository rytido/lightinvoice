window.onload = function(){

    var url = new URL(window.location.href);
    var amt = url.searchParams.get("amt");
    if (amt != null) {

        var eventSource = new EventSource("/success");

        eventSource.onmessage = function(e) {
            if (e.data == "success") {
                alert("payment received!")
            }
        };

    };

};