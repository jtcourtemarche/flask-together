"use strict"

var socket, start_time, start_video, player_initialized;

player_initialized = false;

function reload_online_users(online_users)
{
    // reset active users
    $('.active-users').empty();

    // show all active users
    online_users.forEach(function(user, index) {
        if (user != undefined)
        {
            $('.active-users').append(
                '<div id="'+user+'" class="online-user"></div><i class="fas fa-circle online"></i>&nbsp;<a target="_blank" href="/~'+user+'">'+user+'</a></div>&nbsp;'
            );
        }
    });
}

// Initialize socket events ------------->
var connect_socket = function() {
    if (socket == undefined) {
        // Change socket URL based on request scheme
        var scheme = $('meta[name=scheme]').attr('content');

        socket = io();

        if (scheme == 'https') {
            socket = io.connect('wss://' + document.domain + ':' + location.port, {secure: true});
        } else if (scheme == 'http') {
            socket = io.connect('ws://' + document.domain + ':' + location.port);
        }
    }

    // Handle Connect ----------------------->
    socket.on('connect', function() {
        socket.emit('user:connected', $('meta[name=room]').data('id'));
    });

    socket.on('server:disconnected', function(data) {
        $('.active-users #'+data.user_name).remove();
        console.log('disconnected');
    });
    
    // Load last video from database -------------->
    socket.on('server:sync', function(data) {
        // play most recent video 
        if (Object.keys(data.most_recent).length != 0) {
            player.loadVideoById(data.most_recent.watch_id);
            $('title').html(data.most_recent.title);
            $('.video_title').html("<a href='https://www.youtube.com/watch?v="+data.most_recent.watch_id+"'>"+data.most_recent.title+"</a>");

            player.addEventListener('onStateChange', function a(state) {
                if (state.data == 1 && player_initialized == false) {
                    socket.emit('user:signal-preload', 
                        $('meta[name=room]').data('id')
                    );
                    player_initialized = true;
                }
            });
        }

        $("#history-list").empty();

        // load room history
        if (Object.keys(data.history).length != 0)
        {
            data.history.forEach(function(video) {
                $("#history-list").append("<li id='list-result' class='list-group-item' onclick='controlPlayNew(\"https://www.youtube.com/watch?v=" +
                    video.watch_id + "\")'><p>" + 
                    video.title + "</p><img class='thumbnail' src='" + 
                    video.thumbnail + 
                    "' /></li>");
            });
        } else {
            $("#history-list").append("<span class='no-search'>No history.</span>");
        }

        reload_online_users(data.online_users);

        // Often a browser will auto-refresh the page over time
        // making it so "No search results" will repeat over
        // and over again. To prevent this empty the div.
        $("#search-list").empty();
        $("#search-list").append("<span class='no-search'>No search results.</span>");
    });

    // Handle New User Connect ----------------------->
    socket.on('server:user-joined', function(data) {
        reload_online_users(data.online_users);
    });

    // Handle request for data callback -------------->
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
            player.playVideo();
        } else if (data.state == 2) {
            // Paused
            $('#play').show();
            $('#pause').hide();
            player.pauseVideo();
        } else if (data.state == 3) {
            // Buffering : assume playing
            $('#play').hide();
            $('#pause').show();
            player.playVideo();
        } else if (data.state == 0) {
            // Ended
            $('#replay').show();
            $('#play').hide();
            $('#pause').hide();
            player.pauseVideo();
        } else {
            console.log(data);
            console.log('Could not get player state!');
        }
    });

    // Skip --------------------------------->
    socket.on('server:skip', function (data) {
        player.seekTo(data.time);
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
        player.seekTo(data.time);
        player.playVideo();

        $('#pause').show();
        $('#play').hide();
        $('#replay').hide();
    });
    socket.on('server:pause', function (data) {
        player.seekTo(data.time);
        player.pauseVideo();

        $('#play').show();
        $('#pause').hide();
        $('#replay').hide();
    });
    socket.on('server:rate', function(data) {
        player.setPlaybackRate(data.rate);
        // Cancel previous animation
        $('.playback-rate').stop(true, true).fadeOut(2500);

        $('.playback-rate').show();
        $('.playback-rate').html(data.rate+'x');
        $('.playback-rate').fadeOut(2500);
    });

    // Process playing new video ------------>
    socket.on('server:play-new', function (data) {
        // Reset play button
        $('#pause').show();
        $('#play').hide();
        $('#replay').hide();

        // Set Youtube data
        $('title').html(data.video.title);
        $('.video_title').html("<a target='_blank' href='https://www.youtube.com/watch?v="+data.video.id+"'>"+data.video.title+"</a>");

        // Load new video
        player.loadVideoById(data.video.watch_id);
        player.seekTo(0);
        player.playVideo();

        // Update history list with new video
        $("#history-list").prepend("<li id='list-result' class='list-group-item' onclick='controlPlayNew(\"https://www.youtube.com/watch?v=" +
            data.video.watch_id + "\")'><p>" + 
            data.video.title + "</p><img class='thumbnail' src='" + 
            data.video.thumbnail + 
            "' /></li>");    

        // Scrobble LastFM

        var callback = data;
        // clearing the most recent video info will speed up the transaction
        delete callback.most_recent;

        // Send request to LastFM function to see if the video can be scrobbled
        socket.emit('user:play-callback', {data: JSON.stringify(callback)});
        
        // Clear loading animation
        $('#yt-search').html('Search');

        // Reset LastFM genres
        $('#genres').empty();
    });

    socket.on('server:play-new-artist', function(data) {
        if (data.artist != false) {
            var artist = JSON.parse(data.artist);
            $('#genres').html(artist.tags);
        }
    });

    // Search function ---------------------->
    socket.on('server:serve-list', function (data) {
        $('#yt-search').html('Search');

        if (!data.append) {
            $("#search-list").empty();
        } else {
            $('.load-more').remove();
        }

        if (data.results.length == 0) {
            $("#search-list").append("<span class='no-search'>No results found.</span>");
        } else {
            data.results.forEach(function(video) {
                $("#search-list").append("<li id='list-result' class='list-group-item' onclick='controlPlayNew(\"https://www.youtube.com/watch?v=" +
                    video.id.videoId + "\")'><p>" +
                    video.snippet.title + "</p><img class='thumbnail' alt='Thumbnail Image for "+video.snippet.title+"' src='" +
                    video.snippet.thumbnails.high.url +
                    "' /><span class='upload-date'>"+
                    video.snippet.publishedAt.split('T')[0] +
                    "</span></li>");
            });

            $("#search-list").append("<li id='list-result' class='load-more' tabindex='"+data.results.length+"' class='list-group-item' onclick='controlLoadMore("+data.page+")'><i class='fas fa-chevron-circle-down'></i></li>");
        }

        if (!data.append)
            $('#search-list').scrollTo(0);
    });

    return socket;
};
