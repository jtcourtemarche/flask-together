"use strict"

var player, playback_rates, player_ready, socket;

// Twitch Player

var twplayer = new Twitch.Player(
    "twitch-player", 
    {
        width: $("#progress-bar").width(),
        height: 447,
        channel: 'none',
        autoplay: false,
        allowfullscreen: true,
    }
)

twplayer.addEventListener(Twitch.Player.READY, function() {
    console.log('👍🏼 Twitch player loaded.')
})

var new_stream_played = false;

twplayer.addEventListener(Twitch.Player.PLAYING, function() {
    // Load qualities
    if (new_stream_played) {
        $('#qualities-dropdown').show();
        $('#video-title').html(twplayer.getChannel());
        var qualities = twplayer.getQualities();
            $('#qualities-dropdown').show();
            //$('#qualities-dropdown').empty();
            for (var q in qualities) {
                $('#qualities-dropdown .dropdown-menu').append('<a class="dropdown-item" onclick="twitchChangeQuality(\''+qualities[q].name+'\')">'+qualities[q].name+'</a>')
            }
        new_stream_played = false;
    }
})

function twitchChangeQuality(quality) {
    twplayer.setQuality(quality);
}

// Youtube Player

console.log(window.location.hostname);

function onYouTubeIframeAPIReady() {
    player = new YT.Player('youtube-player', {
        width: $("#progress-bar").width(),
        height: 447,
        videoId: '',
        playerVars: {
            controls: 0,
            cc_load_policy: 0,
            // Removed 9/25/18 (my birthday! thanks Youtube!!)
            rel: 0,
            // Also deprecated as of 9/25/18
            showinfo: 0,
            host: 'localhost',
            origin: 'localhost',
            frameborder: 0,
            iv_load_policy: 3,
            autoplay: 0,
            modestbranding: 1,
            disablekb: 1,
            origin: window.location.hostname,
        },
        events: {
            onReady: onReady,
            onStateChange: stateChange
        }
    });
}

function onReady (event) {
    console.log('👍🏼 Youtube player loaded.')

    updateProgressBar(event.target.getCurrentTime(), event.target.getDuration());
    updateTimerDisplay(event.target.getCurrentTime(), event.target.getDuration());

    if ('captions' in event.target.getOptions()) {
        console.log('Captions available');
    }

    event.target.setVolume(50);

    var time_update_interval = setInterval(function () {
        updateProgressBar();
        updateTimerDisplay();
    }, 1000);

    socket = connect_socket(event.target);
}

function stateChange (event) {
    if (event.data == 5) {
        socket.emit('user:player-ready', event.target);
    }
    if (event.data == 2) {
        controlPause();
    }
    if (event.data == 1) {
        if ($('#play').is(':visible')) {
            controlPlay();
        }
    }
    if (event.data == 0) {
        // Video ended
        $('#play').hide();
        $('#pause').hide();
        $('#replay').show();
    }

    playback_rates = event.target.getAvailablePlaybackRates();
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
    if ($('#twitch-player').is(':visible')) {
        $('#current-time').text(formatTime(twplayer.getCurrentTime()));
        $('#duration').text('Live');   
    } else {
        $('#current-time').text(formatTime(player.getCurrentTime()));
        $('#duration').text(formatTime(player.getDuration()));        
    }
}

function showPlaybackRates(playback_rates) {
    $("#playback-rates").empty();
    for (var p in playback_rates) {
        $("#playback-rates").append("<button onclick='controlRate("+playback_rates[p]+")' class='btn btn-outline-secondary'>"+playback_rates[p]+"</button>");
    }
}

// ------------------------------------------------>

var appendHistory = function(history) {
    $("#history-list").empty();
    for (var h in history.reverse()) {
        if (h > 20) {
            break;
        } else if (h >= history.length) {
            break;
        }

        var prev_video_title;

        if (history[h].video_id.length != 0) {
            // Avoid repeats
            if (prev_video_title != history[h].video_title) {
                prev_video_title = history[h].video_title;
                $("#history-list").append("<li id='list-result' class='list-group-item' onclick='controlPlayNew(\"https://www.youtube.com/watch?v=" +
                history[h].video_id + "\")'><p>" + 
                history[h].video_title + "</p><img class='thumbnail' src='" + 
                history[h].video_thumbnail + 
                "' /><span class='upload-date'>"+ 
                history[h].video_date.split('T')[0] +
                "</span></li>");
            }
        }
    }
};

var controlPlayNew = function (url) {
    if (typeof socket != 'undefined') {
        socket.emit('user:play-new', {
            url: url,
            user: $('#current-user').data(),
        });
    }
};

// Fullscreen --------------------------->
var controlFullscreen = function () {
    if (typeof socket != 'undefined') {
        if ($('twitch-player').is(':visible')) {
            var iframe = document.getElementById("twitch-player"); 
            twplayer.setFullscreen(true);          
        } else {
            var iframe = document.getElementById("youtube-player");
        }
        // Chrome only implementation
        iframe.webkitRequestFullScreen();
    }
};

var controlPlay = function () {
    if (typeof socket != 'undefined') {
        if ($('#twitch-player').is(':visible')) {
            socket.emit('user:play', {
                time: ''
            });     
        } else {
            socket.emit('user:play', {
                time: player.getCurrentTime()
            });            
        }
    }
};
var controlPause = function () {
    if (typeof socket != 'undefined') {
        if ($('#twitch-player').is(':visible')) {
            twplayer.pause();
            socket.emit('user:pause', {
                time: ''
            });
        } else {
            player.pauseVideo();
            socket.emit('user:pause', {
                time: player.getCurrentTime()
            });
        }
        $('#play').show();
        $('#pause').hide();
        $('#replay').hide();
    }
};

// Skip to ------------------------------>
var controlSkip = function (time) {
    var seconds;
    if (typeof socket != 'undefined') {
        if (String(time).indexOf(':') > -1) {
            time = time.split(':');
            if (time.length == 2) {
                seconds = (+time[0]) * 60 + (+time[1]); 
            } else {
                seconds = (+time[0]) * 60 * 60 + (+time[1]) * 60 + (+time[2]); 
            }
            time = seconds;
        }

        socket.emit('user:skip', {
            time: time
        });
    }
};

// Change Playback Rate ----------------->
var controlRate = function (rate) {
    if (typeof socket != 'undefined') {
        socket.emit('user:rate', {
            rate: rate
        });
    }
};
