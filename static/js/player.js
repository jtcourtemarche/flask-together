/*

For most of the code in this file, credit goes to:
https://demo.tutorialzine.com/2015/08/how-to-control-youtubes-video-player-with-javascript/

*/

var player, socket, playback_rates;

window.onYouTubeIframeAPIReady = function () {
    player = new YT.Player('video-placeholder', {
        width: $("#progress-bar").width(),
        height: 447,
        videoId: 'gMslUkDaDZA',
        playerVars: {
            color: 'white',
            controls: 0,
            rel: 0,
            showinfo: 0,
            host: 'https://www.youtube.com',
            origin: 'https://jiejie.stream',
            'frameborder': 0
        },
        events: {
            onReady: initialize,
            onStateChange: stateChange
        }
    });
};

function formatTime(time) {
    time = Math.round(time);

    var minutes = Math.floor(time / 60),
        seconds = time - minutes * 60;

    seconds = seconds < 10 ? '0' + seconds : seconds;

    return minutes + ":" + seconds;
}

// This function is called by initialize()
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
    for (i in playback_rates) {
        $("#playback-rates").append("<button onclick='controlRate("+playback_rates[i]+")' class='btn btn-outline-secondary'>"+playback_rates[i]+"</button>");
    }
}

window.initialize = function (event) {
    if (history_video_id != "") {
        event.target.loadVideoById(history_video_id);
        event.target.playVideo();
    }

    updateProgressBar();
    updateTimerDisplay();

    // Start interval to update elapsed time display and
    // the elapsed part of the progress bar every second.
    var time_update_interval = setInterval(function () {
        updateProgressBar();
        updateTimerDisplay();
    }, 1000);

    //player.setSize({width: $("#resize-video-frame").width, height: $("#resize-video-frame").height});
};

window.stateChange = function (event) {
    $("#page-title").html("<a target='_blank' href='https://www.youtube.com/watch?v=" + event.target.getVideoData()["video_id"] + "'>" + event.target.getVideoData()["title"] + "</a>");
    $("#page-author").html('<button type="button" class="btn btn-secondary btn-sm" disabled>' + event.target.getVideoData()["author"]+'</button>');
    playback_rates = event.target.getAvailablePlaybackRates();
    showPlaybackRates(playback_rates);
};