"use strict"

var socket, start_time, start_video;

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
        // Play last video from DB
        if (data.most_recent != null) {
            console.log('Syncing most recent video @ '+data.most_recent.video_id);
            player.loadVideoById(data.most_recent.video_id);
            $('#page-user').html(data.most_recent_username);
            appendHistory(data.history);

            setTimeout(function() {
                socket.emit('init-preload');
            }, 1000);
        } else {
            $('#history-list').empty();
            $("#history-list").append("<span class='no-search'>No history.</span>");
        }
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

    // Handle Request for Data -------------->
    socket.on('request-data', function(data) {
        socket.emit('preload-info', {
            time: player.getCurrentTime(),
            state: player.getPlayerState(),
            sid: data.sid,
        });
    });

    // Load preload data
    socket.on('preload', function(data) {
        controlSkip(data.time);
        if (data.state == 1) {
            // Playing
            $('#play').hide();
            $('#pause').show();
        } else if (data.state == 2) {
            // Paused
            $('#play').show();
            $('#pause').hide();
        } else if (data.state == 3) {
            // Buffering : assume playing
            $('#play').hide();
            $('#pause').show();
        } else {
            console.log('Could not get player state!');   
        }
    });

    // Skip --------------------------------->
    socket.on('server-skip', function (time) {
        console.log('test2 '+time);
        player.seekTo(time);
        if ($('#play').is(':visible')) {
            $('#play').show();
            $('#pause').hide();
            player.pauseVideo();
        } 
        else {
            $('#pause').show();
            $('#play').hide();
            player.playVideo();
        }
        $('#replay').hide();
    });

    // Play / Pause ------------------------->
    socket.on('server-play', function (time) {
        player.seekTo(time);
        player.playVideo();

        $('#pause').show();
        $('#play').hide();
        $('#replay').hide();
    });
    socket.on('server-pause', function (time) {
        player.seekTo(time);
        player.pauseVideo();
        $('#play').show();
        $('#pause').hide();
        $('#replay').hide();
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

        $('#page-user').html(data.user);

        player.loadVideoById(data.id);
        player.seekTo(0);
        player.playVideo();

        $('#pause').show();
        $('#play').hide();
        $('#replay').hide();
    });

    // Search function ---------------------->
    socket.on('server-serve-list', function (results) {
        $('#yt-search').html('Search');
        $("#search-list").empty();
        var r = 0;
        for (r in results) {
            $("#search-list").append("<li id='list-result' class='list-group-item' onclick='controlPlayNew(\"https://www.youtube.com/watch?v=" +
             results[r].id.videoId + "\")'><p>" + 
             results[r].snippet.title + "</p><img class='thumbnail' src='" + 
             results[r].snippet.thumbnails.high.url + 
             "' /><span class='upload-date'>"+ 
             results[r].snippet.publishedAt.split('T')[0] +
             "</span></li>");
        }
        if (results.length == 0) {
            $("#search-list").append("<span class='no-search'>No results found.</span>");
        }
        $("#search-list").attr('scrollTop', 0);
    });

    return socket;
};
