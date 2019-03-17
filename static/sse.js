window.onload = function(){

    var modal = document.getElementById('success_modal');

    window.onclick = function(event) {
      if (event.target != modal) {
        modal.style.display = "none";
      }
    }

    var url = new URL(window.location.href);
    var amt = url.searchParams.get("amt");
    if (amt != null) {

        var eventSource = new EventSource("/success");

        eventSource.onmessage = function(e) {
            if (e.data == "success") {
                modal.style.display = "block";
            }
        };

    };

};