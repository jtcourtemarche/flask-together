var socket;

var appendHistory = function(history) {
    $("#history-list").empty();
    var data;
    var video_title, video_thumbnail, prev_video_title, video_id;
    for (var h in history.reverse()) {
        if (h > 25) {
            break;
        } else if (h >= history.length) {
            break;
        }

        data = JSON.parse(history[h].data);
        data = JSON.parse(data);
        if (data.items.length != 0) {
            video_title = data.items[0].snippet.title;
            video_date = data.items[0].snippet.publishedAt;
            video_id = history[h].video_id;
            watched_date = history[h].date;
            video_thumbnail = data.items[0].snippet.thumbnails.default.url;

            // Avoid repeats
            if (prev_video_title != video_title) {
                prev_video_title = video_title;
                $("#history-list").append("<li id='list-result' class='list-group-item' onclick='controlPlayNew(\"https://www.youtube.com/watch?v=" + 
                    video_id + "\")'><p>" + video_title + "<br/><span class='upload-date'>" +
                    video_date.split('T')[0]+"</span></p><img class='thumbnail' src='" + video_thumbnail + "'/></li>");
            }
        }
    }
};

var controlPlayNew = function (url) {
    if (typeof socket != 'undefined') {
        socket.emit('client-play-new', {
            url: url,
            user: $('#current-user').data(),
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
    }
};

// Initialize socket events ------------->
var connect_socket = function() {
    if (socket == undefined) {
        socket = io.connect('wss://' + document.domain + ':' + location.port, {secure: true});
        //socket = io.connect('ws://' + document.domain + ':' + location.port);
    }

    // Handle Connect ----------------------->
    socket.on('connect', function() {
        socket.emit('joined');
    });
    
    socket.on('user-disconnected', function(data) {
        console.log(data.username + ' has disconnected');

        $('.active-users').empty();
        var user;
        for (user in data.active_users) {
            if (data.active_users[user][1] == 1) {
                $('.active-users').append('<button class="btn btn-success" disabled>'+data.active_users[user][0]+'</button>&nbsp;');
            } else if (data.active_users[user][1] == 0) {
                $('.active-users').append('<button class="btn btn-secondary" disabled>'+data.active_users[user][0]+'</button>&nbsp;');
            }
        }
    });

    // Load last video from DB -------------->
    socket.on('new-user-sync', function(data) {
        console.log('Playing '+data.most_recent.video_id);

        // Play last video from DB
        if (data.most_recent != []) {
            player.loadVideoById(data.most_recent.video_id);
            player.playVideo();
        }
        
        appendHistory(data.history);
        // Often a browser will auto-refresh the page over time 
        // making it so "No search results" will repeat over 
        // and over again. To prevent this empty the div.
        $("#search-list").empty();
        $("#search-list").append("<span class='no-search'>No search results.</span>");
    });

    // Handle New User Connect ----------------------->
    socket.on('new-user', function(data) {
        $('.active-users').empty();
        var user;
        for (user in data.active_users) {
            if (data.active_users[user][1] == 1) {
                $('.active-users').append('<button class="btn btn-success" disabled>'+data.active_users[user][0]+'</button>&nbsp;');
            } else if (data.active_users[user][1] == 0) {
                $('.active-users').append('<button class="btn btn-secondary" disabled>'+data.active_users[user][0]+'</button>&nbsp;');
            }
        }
    });

    // Skip --------------------------------->
    socket.on('server-skip', function (time) {
        player.seekTo(time);
        if ($('#play').is(':visible')) {
            player.pauseVideo();
        } 
        else {
            player.playVideo();
        }
    });

    // Play / Pause ------------------------->
    socket.on('server-play', function (time) {
        player.seekTo(time);
        player.playVideo();

        $('#pause').show();
        $('#play').hide();
    });
    socket.on('server-pause', function (time) {
        player.seekTo(time);
        player.pauseVideo();

        $('#play').show();
        $('#pause').hide();
    });
    socket.on('server-rate', function(rate) {
        player.setPlaybackRate(rate);
        // Cancel previous animation
        $('.playback-rate').stop(true, true).fadeOut(2500);

        $('.playback-rate').show();
        $('.playback-rate').html(rate+'x');
        $('.playback-rate').fadeOut(2500);
    });

    // Process playing new video ------------>
    socket.on('server-play-new', function (data) {
        appendHistory(data.history);

        $('#page-user').html(data.user_id);

        player.loadVideoById(data.id);
        player.seekTo(0);
        player.playVideo();

        $('#pause').show();
        $('#play').hide();
        $('#replay').hide();
    });

    // Search function ---------------------->
    socket.on('server-serve-list', function (data) {
        $('#yt-url-close-icon').html('&times');
        $("#search-list").empty();
        var r = 0;
        for (r in data.results) {
            $("#search-list").append("<li id='list-result' class='list-group-item' onclick='controlPlayNew(\"https://www.youtube.com/watch?v=" +
             data.results[r].id.videoId + "\")'><p>" + 
             data.results[r].snippet.title + "<br/><span class='upload-date'>"+ 
             data.results[r].snippet.publishedAt.split('T')[0] +
             "</span></p><img class='thumbnail' src='" + 
             data.results[r].snippet.thumbnails.high.url + 
             "'/></li>");
        }
        if (data.results.length == 0) {
            $("#search-list").append("<span class='no-search'>No results found.</span>");
        }
        document.querySelector("#search-list").scrollTop = 0;
    });
};
