"use strict"

var player, si; 
var player_states = {
    UNSTARTED: -1,
    ENDED: 0,
    PLAYING: 1,
    PAUSED: 2,
    BUFFERING: 3,
    CUED: 5
}

// initialize Youtube player
function onYouTubeIframeAPIReady() {
    player = new YT.Player('youtube-player', {
        width: $("#progress-bar").width(),
        height: 447,
        videoId: '',
        playerVars: {
            controls: 0,
            cc_load_policy: 0,
            host: 'localhost',
            origin: 'localhost',
            iv_load_policy: 3,
            autoplay: 1,
            modestbranding: 1,
            disablekb: 1
        },
        events: {
            'onReady': onReady,
            'onStateChange': stateChange
        }
    });
}

function onReady (event) {
    console.log('👍🏼 Youtube player loaded.')

    // close loading screen
    $('.loading-screen').css('display', 'none');

    updateProgressBar(event.target.getCurrentTime(), event.target.getDuration());
    updateTimerDisplay(event.target.getCurrentTime(), event.target.getDuration());

    event.target.unMute();
    event.target.setVolume(50);

    var time_update_interval = setInterval(function () {
        updateProgressBar();
        updateTimerDisplay();
    }, 1000);

    si = new SocketInterface(player);
}

function stateChange (event) {
    if (event.data == 0) {
        // Video ended
        $('#play').hide();
        $('#pause').hide();
        $('#replay').show();
    }

    var playback_rates = event.target.getAvailablePlaybackRates();
    showPlaybackRates(playback_rates);
}

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
        $("#playback-rates").append("<a class='dropdown-item' onclick='si.controlRate("+playback_rates[p]+")'>"+playback_rates[p]+"</a>");
    }
}
