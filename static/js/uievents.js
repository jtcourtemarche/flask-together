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
			/*
			!!! Volume key binds no longer supported

			case 187:
				// +

				if ($('#youtube-player').css('display') == 'none') {
					vol = TwitchPlayer.getVolume() + 5;
					if (TwitchPlayer.getVolume() >= 100) {
						vol = 100;
					}
					TwitchPlayer.setVolume(vol);
				}
				else {
					vol = player.getVolume() + 5;
					if (player.getVolume() >= 100) {
						vol = 100;
					}
					player.setVolume(vol);
				}

				$('#volume-slider').val(vol);
				$('#volume-display').stop().animate({opacity:'100'});
				$('#volume-display').show();
				$('#volume-display').html(vol+'%');
				$('#volume-display').fadeOut(1000);
				break;
			case 189:
				// -

				if ($('#youtube-player').css('display') == 'none') {
					vol = TwitchPlayer.getVolume() - 5;
					if (TwitchPlayer.getVolume() <= 0) {
						vol = 0;
					}
					TwitchPlayer.setVolume(vol);
				} else {
					vol = player.getVolume() - 5;
					if (player.getVolume() <= 0) {
						vol = 0;
					}
					player.setVolume(vol);
				}

				$('#volume-slider').val(vol);
				$('#volume-display').stop().animate({opacity:'100'});
				$('#volume-display').show();
				$('#volume-display').html(vol+'%');
				$('#volume-display').fadeOut(1000);
				break;
			*/
		}
	}
});

$('#list-result').on('keypress', function(event) {
	console.log(event);
	if (event.which == 13) {
		this.click();
	}
});

$("#volume-slider").on('input', function() {
	if ($('#youtube-player').css('display') == 'none') {
		TwitchPlayer.setMuted(false);
		TwitchPlayer.setVolume($("#volume-slider").val() * 0.01);	
	}
	else {
		player.setVolume($("#volume-slider").val());	
	}

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
	controlSkip(newTime);
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
	$('#yt-url').focus();
});

// Make play/pause toggleable
$('#play, #pause').click(function() {
	$('#play, #pause').toggle();
});
$('#replay').click(function() {
	$('#replay').hide();
});
