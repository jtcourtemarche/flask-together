// jQuery Event Functions

$('html').on('keydown', function(event) {
	// Shortcuts
	// Make sure inputs aren't selected
	var vol;
	if ($('#yt-url').is(':focus') == false && $('#skip_to').is(':focus') == false) {
		switch (event.which) {
			case 70:
				// F
				controlFullscreen();
				break;
			case 187:
				// +
				vol = player.getVolume() + 5;
				if (player.getVolume() >= 100) {
					vol = 100;
				}
				player.setVolume(vol);
				$('#volume-slider').val(vol);

				$('#volume-display').stop().animate({opacity:'100'});
				$('#volume-display').show();
				$('#volume-display').html(vol+'%');
				$('#volume-display').fadeOut(1000);
				break;
			case 189:
				// -
				vol = player.getVolume() - 5;
				if (player.getVolume() <= 0) {
					vol = 0;
				}
				player.setVolume(vol);
				$('#volume-slider').val(vol);

				$('#volume-display').stop().animate({opacity:'100'});
				$('#volume-display').show();
				$('#volume-display').html(vol+'%');
				$('#volume-display').fadeOut(1000);
				break;
		}
	}
});

$("#volume-slider").on('input', function() {
	player.setVolume($("#volume-slider").val());
	$('#volume-display').stop().animate({opacity:'100'});
	$('#volume-display').show();
	$('#volume-display').html($('#volume-slider').val()+'%');
});
$('#volume-slider').on('mouseup', function() {
	$('#volume-display').fadeOut(1000);
});

$('#progress-bar').on('click touchend', function (e) {
	// Calculate the new time for the video.
	var newTime = player.getDuration() * (e.target.value / 100);
	socket.emit('client-skip', {time: newTime});
});

$('#yt-url').on("keydown", function(event) {
	if ($('#yt-url').val().indexOf('://www.youtube.com/watch?v=') == -1) {
		if (event.which == 13) {
			$('#yt-search').html('<img class="spinner" src="../static/images/spinner.gif"/>');
			controlPlayNew($("#yt-url").val());
		}
	} else if (event.which == 13) {
		$('#yt-search').html('<img class="spinner" src="../static/images/spinner.gif"/>');
		controlPlayNew($("#yt-url").val());
	}
})
$('#yt-search').on('click', function() {
	if ($('#yt-url').val().indexOf('://www.youtube.com/watch?v=') == -1) {
		$('#yt-search').html('<img class="spinner" src="../static/images/spinner.gif"/>');
	}
	controlPlayNew($("#yt-url").val());
});

$('#skip_to').on("keydown", function(event) {
	if (event.which == 13) {
		controlSkip($("#skip_to").val());
	}
});

$('#yt-url-close').click(function() {
	$('#yt-url').val('');
});

// Make play/pause toggleable
$('#play, #pause').click(function() {
	$('#play, #pause').toggle();
});
$('#replay').click(function() {
	$('#replay').hide();
});

$('.embed-responsive').mouseenter(function() {
	$('#video-overlay').fadeIn(100);
});
$('.embed-responsive').mouseleave(function() {
	$('#video-overlay').fadeOut(0);
});

// Cancel overlay fade out on these click events
$('#video-overlay #page-title').mouseenter(function() {
	$('#video-overlay').fadeIn(0);
});
$('#video-overlay #page-artist').mouseenter(function() {
	$('#video-overlay').fadeIn(0);
});

