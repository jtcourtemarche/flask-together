var appendHistory = function(history) {
    $("#history-list").empty();
    var json, video_title, video_thumbnail, prev_video_title, video_id;
    for (i in history) {
        if (i > 20) {
            break;
        }

        json = JSON.parse(history[i][2]);
        video_title = json.items[0].snippet.title;
        video_id = json.items[0].id;
        video_thumbnail = json.items[0].snippet.thumbnails.default.url;
        // Avoid repeats
        if (prev_video_title != video_title) {
            prev_video_title = video_title;
            $("#history-list").append("<li class='list-group-item'><div class='history-result' onclick='controlPlayNew(\"https://www.youtube.com/watch?v=" + video_id + "\")'><p>" + video_title + "</p><img class='thumbnail' src='" + video_thumbnail + "'/></div></li>");
        }
    }
}

// Initialize socket events ------------->
socket = io.connect('https://' + document.domain + ':' + location.port);

// Handle Connect ----------------------->
socket.on('connect', function () {
    socket.emit('joined');
});

// Load last video from DB -------------->
history_video_id = "";
socket.on('new-user-sync', function (id) {
    history_video_id = id["id"];
    appendHistory(id["history"]);
    $("#search-list").append("No search results.");
});

// Skip --------------------------------->
socket.on('server-skip', function (time) {
    player.seekTo(time);
    player.playVideo();
});

// Play / Pause ------------------------->
socket.on('server-play', function (time) {
    player.seekTo(time);
    player.playVideo();
});
socket.on('server-pause', function (time) {
    player.seekTo(time);
    player.pauseVideo();
});
controlPlay = function () {
    socket.emit('client-play', {
        time: player.getCurrentTime()
    });
};
controlPause = function () {
    socket.emit('client-pause', {
        time: player.getCurrentTime()
    });
};

// Skip to ------------------------------>
controlSkip = function (time) {
    var time = time.split(':');
    if (time.length == 2) {
        seconds = (+time[0]) * 60 + (+time[1]); 
    } else {
        seconds = (+time[0]) * 60 * 60 + (+time[1]) * 60 + (+time[2]); 
    }

    socket.emit('client-skip', {
        time: seconds
    });
};

// Change Playback Rate ----------------->
controlRate = function (rate) {
    socket.emit('client-rate', {
        rate: rate
    });
};
socket.on('server-rate', function(rate) {
    player.setPlaybackRate(rate);
});

// Fullscreen --------------------------->
controlFullscreen = function () {
    // Chrome only
    var iframe = document.getElementById("video-placeholder");
    iframe.webkitRequestFullScreen();
}

// Process playing new video ------------>
socket.on('server-play-new', function (data) {
    appendHistory(data["history"]);

    player.loadVideoById(data["id"]);
    player.seekTo(0);
    player.playVideo();
});
controlPlayNew = function (url) {
    socket.emit('client-play-new', {
        url: url
    });
};

// Search function ---------------------->
socket.on('server-serve-list', function (data) {
    $("#search-list").empty();
    for (result in data["results"]) {
        $("#search-list").append("<li class='list-group-item'><div class='search-result' onclick='controlPlayNew(\"https://www.youtube.com/watch?v=" + data["results"][result]["id"]["videoId"] + "\")' style='cursor:pointer'><p>" + data["results"][result]["snippet"]["title"] + "</p><img class='thumbnail' src='" + data["results"][result]["snippet"]["thumbnails"]["default"]["url"] + "'/></div></li>");
    }
    if (data["results"].length == 0) {
        $("#search-list").append("<li class='list-group-item disabled'>No results found.</li>");
    }
    document.querySelector("#search-list").scrollTop = 0;
});