// jQuery Event Functions

$('#progress-bar').on('mouseup touchend', function (e) {
	// Calculate the new time for the video.
	var newTime = player.getDuration() * (e.target.value / 100);
	socket.emit('client-skip', {time: newTime});
});

$('#yt-url').on("keydown", function(event) {
	if (event.which == 13) {
	  controlPlayNew($("#yt-url").val());
	}
});

$("#volume-slider").on('input', function() {
	player.setVolume($("#volume-slider").val());
});  

$('#skip_to').on("keydown", function(event) {
	if (event.which == 13) {
		controlSkip($("#skip_to").val());
	}
});

$('#yt-url-close').click(function() {
	$('#yt-url').val('');
});

$('#search-result').click(function() {
	//
});

// Make play/pause toggleable
$('#play, #pause').click(function() {
	$('#play, #pause').toggle();
});