var socket;

var appendHistory = function(history) {
    $("#history-list").empty();
    var json, video_title, video_thumbnail, prev_video_title, video_id;
    for (var h in history) {
        if (h > 20) {
            break;
        }

        json = JSON.parse(history[h][2]);
        video_title = json.items[0].snippet.title;
        video_id = json.items[0].id;
        video_date = json.items[0].snippet.publishedAt;
        video_thumbnail = json.items[0].snippet.thumbnails.default.url;
        // Avoid repeats
        if (prev_video_title != video_title) {
            prev_video_title = video_title;
            $("#history-list").append("<li id='list-result' class='list-group-item' onclick='controlPlayNew(\"https://www.youtube.com/watch?v=" + 
                video_id + "\")'><p>" + video_title + "<br/><span class='upload-date'>" +
                video_date.split('T')[0]+"</span></p><img class='thumbnail' src='" + video_thumbnail + "'/></li>");
        }
    }
};

var controlPlayNew = function (url) {
    if (typeof socket != 'undefined') {
        socket.emit('client-play-new', {
            url: url
        });
    }
};

// Fullscreen --------------------------->
var controlFullscreen = function () {
    if (typeof socket != 'undefined') {
        // Chrome only
        var iframe = document.getElementById("video-placeholder");
        iframe.webkitRequestFullScreen();
    }
};

var controlPlay = function () {
    if (typeof socket != 'undefined') {
        socket.emit('client-play', {
            time: player.getCurrentTime()
        });
    }
};
var controlPause = function () {
    if (typeof socket != 'undefined') {
        socket.emit('client-pause', {
            time: player.getCurrentTime()
        });
    }
};

// Skip to ------------------------------>
var controlSkip = function (time) {
    if (typeof socket != 'undefined') {
        time = time.split(':');
        if (time.length == 2) {
            seconds = (+time[0]) * 60 + (+time[1]); 
        } else {
            seconds = (+time[0]) * 60 * 60 + (+time[1]) * 60 + (+time[2]); 
        }

        socket.emit('client-skip', {
            time: seconds
        });
    }
};

// Change Playback Rate ----------------->
var controlRate = function (rate) {
    if (typeof socket != 'undefined') {
        socket.emit('client-rate', {
            rate: rate
        });
        // Cancel previous animation
        $('.playback-rate').stop(true, true).fadeOut(2500);

        $('.playback-rate').show();
        $('.playback-rate').html(rate+'x');
        $('.playback-rate').fadeOut(2500);
    }
};

// Initialize socket events ------------->
var connect_socket = function() {
    if (socket == undefined) {
        socket = io.connect('wss://' + document.domain + ':' + location.port, {secure: true});
        //socket = io.connect('ws://' + document.domain + ':' + location.port);
    }

    // Handle Connect ----------------------->
    socket.on('connect', function () {
        socket.emit('joined');
    });

    // Load last video from DB -------------->
    socket.on('new-user-sync', function (id) {
        history_video_id = id.id;
        console.log('Playing '+history_video_id);

        // Play last video from DB
        if (history_video_id != []) {
            player.loadVideoById(history_video_id);
            player.playVideo();
        }

        appendHistory(id.history);
        // Often a browser will auto-refresh the page over time 
        // making it so "No search results" will repeat over 
        // and over again. To prevent this empty the div.
        $("#search-list").empty();
        $("#search-list").append("<span class='no-search'>No search results.</span>");
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
    socket.on('server-rate', function(rate) {
        player.setPlaybackRate(rate);
    });

    // Process playing new video ------------>
    socket.on('server-play-new', function (data) {
        appendHistory(data.history);

        player.loadVideoById(data.id);
        player.seekTo(0);
        player.playVideo();
    });

    // Search function ---------------------->
    socket.on('server-serve-list', function (data) {
        $("#search-list").empty();
        for (var result in data.results) {
            $("#search-list").append("<li id='list-result' class='list-group-item' onclick='controlPlayNew(\"https://www.youtube.com/watch?v=" +
             data.results[result].id.videoId + "\")'><p>" + 
             data.results[result].snippet.title + "<br/><span class='upload-date'>"+ 
             data.results[result].snippet.publishedAt.split('T')[0] +
             "</span></p><img class='thumbnail' src='" + 
             data.results[result].snippet.thumbnails.high.url + 
             "'/></li>");
        }
        if (data.results.length == 0) {
            $("#search-list").append("<span class='no-search'>No results found.</span>");
        }
        document.querySelector("#search-list").scrollTop = 0;
    });
};
