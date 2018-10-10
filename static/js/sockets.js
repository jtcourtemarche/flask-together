"use strict"

var socket, start_time, start_video;

// Initialize socket events ------------->
var connect_socket = function() {
    if (socket == undefined) {
        // Change socket URL based on request scheme 
        var scheme = $('meta[name=scheme]').attr('content');
        if (scheme == 'https') {
            socket = io.connect('wss://' + document.domain + ':' + location.port, {secure: true});
        } else if (scheme == 'http') {
            socket = io.connect('ws://' + document.domain + ':' + location.port);
        }
    }

    // Handle Connect ----------------------->
    socket.on('connect', function() {
        socket.emit('user:joined');
    });
    
    socket.on('server:disconnected', function(data) {
        $('.active-users').empty();
        var user;
        for (user in data.active_users) {
            if (data.active_users[user][1] == 1) {
                $('.active-users').append('<i class="fas fa-circle online"></i>&nbsp;<a target="_blank" href="/~'+data.active_users[user][0]+'">'+data.active_users[user][0]+'</a>&nbsp;');
            } else if (data.active_users[user][1] == 0) {
                $('.active-users').append('<i class="fas fa-circle offline"></i>&nbsp;<a target="_blank" href="/~'+data.active_users[user][0]+'">'+data.active_users[user][0]+'</a>&nbsp;');
            }
        }
    });

    // Load last video from DB -------------->
    socket.on('server:sync', function(data) {
        // Play last video from DB
        if (data.most_recent != null && data.most_recent_username != null) {
            player.loadVideoById(data.most_recent.video_id);
            $('#page-user').html(data.most_recent_username);
            $('title').html(data.most_recent.video_title);
            appendHistory(data.history);

            setTimeout(function() {
                socket.emit('user:init-preload');
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
    socket.on('server:new-user', function(data) {
        $('.active-users').empty();
        var user;
        for (user in data.active_users) {
            if (data.active_users[user][1] == 1) {
                $('.active-users').append('<i class="fas fa-circle online"></i>&nbsp;<a target="_blank" href="/~'+data.active_users[user][0]+'">'+data.active_users[user][0]+'</a>&nbsp;');
            } else if (data.active_users[user][1] == 0) {
                $('.active-users').append('<i class="fas fa-circle offline"></i>&nbsp;<a target="_blank" href="/~'+data.active_users[user][0]+'">'+data.active_users[user][0]+'</a>&nbsp;');
            }
        }
    });

    // Handle Request for Data -------------->
    socket.on('server:request-data', function(data) {
        socket.emit('user:preload-info', {
            time: player.getCurrentTime(),
            state: player.getPlayerState(),
            sid: data.sid,
        });
    });

    // Load preload data
    socket.on('server:preload', function(data) {
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
        } else if (data.state == 0) {
            // Ended
            $('#replay').show();
            $('#play').hide();
            $('#pause').hide();
            player.pauseVideo();
        } else {
            console.log('Could not get player state!');   
        }
    });

    // Skip --------------------------------->
    socket.on('server:skip', function (data) {
        player.seekTo(data['time']);
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

    // Controls ------------------------->
    socket.on('server:play', function (data) {
        player.seekTo(data['time']);
        player.playVideo();

        $('#pause').show();
        $('#play').hide();
        $('#replay').hide();
    });
    socket.on('server:pause', function (data) {
        player.seekTo(data['time']);
        player.pauseVideo();
        $('#play').show();
        $('#pause').hide();
        $('#replay').hide();
    });
    socket.on('server:rate', function(data) {
        player.setPlaybackRate(data['rate']);
        // Cancel previous animation
        $('.playback-rate').stop(true, true).fadeOut(2500);

        $('.playback-rate').show();
        $('.playback-rate').html(data['rate']+'x');
        $('.playback-rate').fadeOut(2500);
    });

    // Process playing new video ------------>
    socket.on('server:play-new', function (data) {
        $('#yt-search').html('Search');

        appendHistory(data.history);

        $('#page-user').html(data.user);
        $('title').html(data.title);

        player.loadVideoById(data.id);
        player.seekTo(0);
        player.playVideo();

        $('#pause').show();
        $('#play').hide();
        $('#replay').hide();
        // Reset LastFM genres
        $('#genres').html();

        $('#video-overlay #page-artist').empty();

        // Clear history from data to send to server 
        // clearing the history will speed up the transaction
        var callback = data;
        callback.history = null;
        console.log(callback);
        socket.emit('user:play-callback', {data: JSON.stringify(callback)});
    });

    socket.on('server:play-new-artist', function(data) {
        if (data.artist != false) {
            var artist = JSON.parse(data.artist);
            $('#video-overlay #page-artist').html(
                "<a target='_blank' href='https://www.last.fm/music/"+artist.name.replace(' ', '+')+"'><img src='"+artist.image[2]['#text']+"'></img></a>"
            );
            console.log(artist);
            $('#genres').html(artist.tags);
        } else {
            $('#video-overlay #page-artist').empty();
        }        
    });

    // Search function ---------------------->
    socket.on('server:serve-list', function (results) {
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
        $('#search-list').scrollTo(0);
    });

    return socket;
};
