var player, playback_rates, player_ready;

function onYouTubeIframeAPIReady() {
    player = new YT.Player('video-placeholder', {
        width: $("#progress-bar").width(),
        height: 447,
        videoId: 'gMslUkDaDZA',
        playerVars: {
            color: 'white',
            controls: 0,
            rel: 0,
            showinfo: 0,
            host: 'localhost',
            origin: 'localhost',
            'frameborder': 0
        },
        events: {
            onReady: onReady,
            onStateChange: stateChange
        }
    });
}

window.onReady = function (event) {
    updateProgressBar();
    updateTimerDisplay();

    var time_update_interval = setInterval(function () {
        updateProgressBar();
        updateTimerDisplay();
    }, 1000);

    connect_socket();
};

window.stateChange = function (event) {
    if (event.data == 5) {
        socket.emit('player-ready', event.target);
    }
    
    $("#page-title").html("<a target='_blank' href='https://www.youtube.com/watch?v=" + event.target.getVideoData().video_id + "'>" + event.target.getVideoData().title + "</a>");
    $("#page-author").html('<button type="button" class="btn btn-secondary btn-sm" disabled>' + event.target.getVideoData().author+'</button>');
    playback_rates = event.target.getAvailablePlaybackRates();
    showPlaybackRates(playback_rates);
};

function formatTime(time) {
    time = Math.round(time);
    var minutes = Math.floor(time / 60), seconds = time - minutes * 60;
    seconds = seconds < 10 ? '0' + seconds : seconds;
    return minutes + ":" + seconds;
}

function updateProgressBar() {
    // Update the value of our progress bar accordingly.
    $('#progress-bar').val((player.getCurrentTime() / player.getDuration()) * 100);
}

function updateTimerDisplay() {
    // Update current time text display.
    $('#current-time').text(formatTime(player.getCurrentTime()));
    $('#duration').text(formatTime(player.getDuration()));
}

function showPlaybackRates(playback_rates) {
    $("#playback-rates").empty();
    for (var p in playback_rates) {
        $("#playback-rates").append("<button onclick='controlRate("+playback_rates[p]+")' class='btn btn-outline-secondary'>"+playback_rates[p]+"</button>");
    }
}