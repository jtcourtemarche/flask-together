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
        for (var user in data.active_users) {
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
        if (data.most_recent != null) {
            if (data.most_recent.player == 'twitch')
            {
                // Hide YT player elements
                $('#duration-container').css('display', 'none');
                $('#playback-rates-dropdown').css('display', 'none');
                $('#skip_to').css('display', 'none');
                $('#progress-bar').css('display', 'none');
                $('.video_title').css('display', 'none');

                // Show Twitch elements
                $('#twitch-info-bar').css('display', 'block');

                // Switch to Twitch player
                $('#youtube-player').css('display', 'none');
                $('#twitch-player').css('display', 'block');

                // Stop Youtube video if one is playing
                player.stopVideo()

                // Play channel
                TwitchPlayer.setChannel(data.most_recent.video_id);

                // Set Twitch data
                $('title').html(data.most_recent.video_id + ' [Twitch]');
                $('.twitch-avatar').attr('src', data.most_recent.twitch_avatar);
                $('.twitch-channel').text(data.most_recent.video_id);
                $('.twitch-title').text(data.most_recent.video_title);

            } else if (data.most_recent.player == 'youtube') {
                player.loadVideoById(data.most_recent.video_id);
                $('title').html(data.most_recent.video_title);
                $('.video_title').html("<a href='https://www.youtube.com/watch?v="+data.most_recent.video_id+"'>"+data.most_recent.video_title+"</a>");
                
                player.addEventListener('onStateChange', function YTplayingListener(state) {
                    if (state.data == 1) {
                        socket.emit('user:init-preload');
                        player.removeEventListener('onStateChange', YTplayingListener, true);
                    }
                });
            }
            preloadHistory(data.history);
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
        // Check which player is being used
        if ($('#youtube-player').css('display') == 'none') {
            TwitchPlayer.play();
        } else {
            player.seekTo(data['time']);    
            player.playVideo();
        }

        $('#pause').show();
        $('#play').hide();
        $('#replay').hide();
    });
    socket.on('server:pause', function (data) {
        // Check which player is being used
        if ($('#youtube-player').css('display') == 'none') {
            TwitchPlayer.pause();
        } else {
            player.seekTo(data['time']);
            player.pauseVideo();
        }

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
        // Reset play button
        $('#pause').show();
        $('#play').hide();
        $('#replay').hide();

        if (data.player == 'youtube') {
            // Case for if Twitch player switched to Youtube player
            if ($('#youtube-player').css('display') == 'none')
            {
                // Pause active Twitch player
                TwitchPlayer.pause();

                // Switch to Youtube player
                $('#youtube-player').css('display', 'block');
                $('#twitch-player').css('display', 'none');

                // Show YT elements
                $('#duration-container').css('display', 'block');
                $('#playback-rates-dropdown').css('display', 'block');
                $('#skip_to').css('display', 'block');
                $('#progress-bar').css('display', 'block');
                $('.video_title').css('display', 'block');

                // Hide Twitch elements
                $('#twitch-info-bar').css('display', 'none');

                // Set volume 
                player.setVolume($('#volume-slider').val());
            }

            // Set Youtube data
            $('title').html(data.title);
            $('.video_title').html("<a target='_blank' href='https://www.youtube.com/watch?v="+data.id+"'>"+data.title+"</a>");

            // Load new video
            player.loadVideoById(data.id[0]);
            player.seekTo(0);   
            player.playVideo();

            // Update history bar
            appendHistory(data.history, data.player);

            // Scrobble LastFM

            var callback = data;
            // Clear history from data to send to server 
            // clearing the history will speed up the transaction
            delete callback.history;
            delete callback.player;
            callback.duration = callback.content.contentDetails.duration;
            delete callback.content;

            // Send request to LastFM function to see if the video can be scrobbled
            socket.emit('user:play-callback', {data: JSON.stringify(callback)});
        }
        else if (data.player == 'twitch')
        {
            // Case for if Youtube player switched to Twitch player
            if ($('#youtube-player').css('display') != 'none')
            {
                // Hide YT player elements
                $('#duration-container').css('display', 'none');
                $('#playback-rates-dropdown').css('display', 'none');
                $('#skip_to').css('display', 'none');
                $('#progress-bar').css('display', 'none');
                $('.video_title').css('display', 'none');

                // Stop Youtube video if one is playing
                player.stopVideo();

                // Switch to Twitch player
                $('#youtube-player').css('display', 'none');
                $('#twitch-player').css('display', 'block');

                // Show Twitch elements
                $('#twitch-info-bar').css('display', 'block');
            }

            // Play channel
            TwitchPlayer.setChannel(data.channel);

            // Set Twitch data
            $('title').html(data.channel + ' [Twitch]');
            $('.twitch-avatar').attr('src', data.avatar);
            $('.twitch-channel').text(data.channel);
            $('.twitch-title').text(data.title);

            // Set volume
            TwitchPlayer.setVolume($('#volume-slider').val() * 0.01);

            // Update history bar
            appendHistory(data.history, data.player);
        }
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
    socket.on('server:serve-list', function (results, append, page) {
        $('#yt-search').html('Search');

        if (!append)
            $("#search-list").empty();
        else { 
            $('.load-more').remove();
        }

        if (results.length == 0) {
            $("#search-list").append("<span class='no-search'>No results found.</span>");
        } else {
            for (var r in results) {
                $("#search-list").append("<li id='list-result' tabindex='"+r+"' class='list-group-item' onclick='controlPlayNew(\"https://www.youtube.com/watch?v=" +
                 results[r].id.videoId + "\")'><p>" + 
                 results[r].snippet.title + "</p><img class='thumbnail' alt='Thumbnail Image for "+results[r].snippet.title+"' src='" + 
                 results[r].snippet.thumbnails.high.url + 
                 "' /><span class='upload-date'>"+ 
                 results[r].snippet.publishedAt.split('T')[0] +
                 "</span></li>");
            }
            $("#search-list").append("<li id='list-result' class='load-more' tabindex='"+results.length+"' class='list-group-item' onclick='controlLoadMore("+page+")'><i class='fas fa-chevron-circle-down'></i></li>");
        }

        if (!append)
            $('#search-list').scrollTo(0);
    });

    return socket;
};

