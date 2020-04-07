"use strict"

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

// contains all socket events and control handlers
class SocketInterface {
    constructor(player) {
        // establish socket
        this.socket = io();

        var scheme = $('meta[name=scheme]').attr('content');
        switch(scheme)
        {
            case 'https':
                this.socket.connect('wss://' + document.domain + ':' + location.port, {secure: true});  
                break;
            case 'http':
                this.socket.connect('ws://' + document.domain + ':' + location.port);
                break;
            default:
                alert('Failed to initialize web sockets!');
        }

        // define socket events 

        this.socket.on('connect', () => {
            this.socket.emit('user:connected', $('meta[name=room]').data('id'));
        });

        this.socket.on('server:disconnected', (data) => {
            $('.active-users #'+data.user_name).remove();
        });

        // sync video data, history, and online users with room
        this.socket.on('server:sync', (data) => {
            // play most recent video 
            if (Object.keys(data.most_recent).length != 0) {
                player.loadVideoById(data.most_recent.watch_id);
                $('title').html(data.most_recent.title);
                $('.video_title').html("<a href='https://www.youtube.com/watch?v="+data.most_recent.watch_id+"'>"+data.most_recent.title+"</a>");
            }

            // load room history
            $("#history-list").empty();
            if (Object.keys(data.history).length != 0)
            {
                data.history.forEach(function(video) {
                    $("#history-list").append("<li id='list-result' class='list-group-item' onclick='si.controlPlayNew(\"https://www.youtube.com/watch?v=" +
                        video.watch_id + "\")'><p>" + 
                        video.title + "</p><img class='thumbnail' src='" + 
                        video.thumbnail + 
                        "' /></li>");
                });
            } else {
                $("#history-list").append("<span class='no-search'>No history.</span>");
            }

            // often a browser will auto-refresh the page over time
            // making it so "No search results" will repeat over
            // and over again. To prevent this empty the div.
            $("#search-list").empty();
            $("#search-list").append("<span class='no-search'>No search results.</span>");

            reload_online_users(data.online_users);
        });

        // handle when new user joins the room 
        this.socket.on('server:user-joined', (data, callback) => {
            reload_online_users(data.online_users);

            // pass player time and state to new user
            callback(player.getCurrentTime(), player.getPlayerState(), data.sid);
        });

        // sync player time and state with other users in room
        this.socket.on('server:time-state-sync', (data) => {
            //this.controlSkip(data.time);
            player.seekTo(data.time);
            
            switch(data.state)
            {
                case player_states.PLAYING:
                    $('#play').hide();
                    $('#pause').show();
                    player.playVideo();
                    break;
                case player_states.PAUSED:  
                    $('#play').show();
                    $('#pause').hide();
                    player.pauseVideo();
                    break;
                case player_states.BUFFERING:
                    $('#play').hide();
                    $('#pause').show();
                    player.playVideo();
                    break;
                case player_states.ENDED:
                    $('#replay').show();
                    $('#play').hide();
                    $('#pause').hide();
                    player.pauseVideo();
                    break;
                default:
                    console.log('Failed to get player state: ', data.state);
            }
        });

        this.socket.on('server:play', (data) => {
            player.seekTo(data.time);
            player.playVideo();

            $('#pause').show();
            $('#play').hide();
            $('#replay').hide();
        });

        this.socket.on('server:pause', (data) => {
            player.seekTo(data.time);
            player.pauseVideo();

            $('#play').show();
            $('#pause').hide();
            $('#replay').hide();
        });

        this.socket.on('server:skip', (data) => {
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

        this.socket.on('server:rate', (data) => {
            player.setPlaybackRate(data.rate);
            // cancel previous animation
            $('.playback-rate').stop(true, true).fadeOut(2500);

            $('.playback-rate').show();
            $('.playback-rate').html(data.rate+'x');
            $('.playback-rate').fadeOut(2500);
        });

        // handle playing new video
        this.socket.on('server:play-new', (data) => {
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
            $("#history-list").prepend("<li id='list-result' class='list-group-item' onclick='si.controlPlayNew(\"https://www.youtube.com/watch?v=" +
                data.video.watch_id + "\")'><p>" + 
                data.video.title + "</p><img class='thumbnail' src='" + 
                data.video.thumbnail + 
                "' /></li>");    

            // Scrobble LastFM

            var callback = data;
            // clearing the most recent video info will speed up the transaction
            delete callback.most_recent;

            // Send request to LastFM function to see if the video can be scrobbled
            this.socket.emit('user:play-callback', {data: JSON.stringify(callback)});
            
            // Clear loading animation
            $('#yt-search').html('Search');

            // Reset LastFM genres
            $('#genres').empty();
        });

        this.socket.on('server:play-new-artist', (data) => {
            if (data.artist != false) {
                var artist = JSON.parse(data.artist);
                $('#genres').html(artist.tags);
            }
        });

        // Search function ---------------------->
        this.socket.on('server:serve-list', (data) => {
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
                    $("#search-list").append("<li id='list-result' class='list-group-item' onclick='si.controlPlayNew(\"https://www.youtube.com/watch?v=" +
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
    }

    // SHARED CONTROLS
    controlPlayNew(url) {
        this.socket.emit('user:play-new', 
            $('meta[name=room]').data('id'),
            url
        );
    };

    controlPlay() {
        this.socket.emit('user:play', 
            $('meta[name=room]').data('id'),
            player.getCurrentTime()
        );            
    };

    controlPause() {
        this.socket.emit('user:pause', 
            $('meta[name=room]').data('id'),
            player.getCurrentTime()
        );
        $('#play').show();
        $('#pause').hide();
        $('#replay').hide();
    };

    // Skip to 
    controlSkip(time) {
        var seconds;
        if (String(time).indexOf(':') > -1) {
            time = time.split(':');
            if (time.length == 2) {
                seconds = (+time[0]) * 60 + (+time[1]); 
            } else {
                seconds = (+time[0]) * 60 * 60 + (+time[1]) * 60 + (+time[2]); 
            }
            time = seconds;
        }
        this.socket.emit('user:skip', 
            $('meta[name=room]').data('id'), 
            time
        );
    };

    // Change Playback Rate 
    controlRate(rate) {
        this.socket.emit('user:rate', 
            $('meta[name=room]').data('id'),
            rate
        );
    };

    controlLoadMore(page) {
        this.socket.emit('user:search-load-more', 
            $('meta[name=room]').data('id'),
            $('#yt-url').val(),
            page
        );
    }

    // LOCAL CONTROLS 

    controlFullscreen() {
        var iframe = document.querySelector("#youtube-player");

        iframe.requestFullscreen().catch(err => {
            alert('Browser did not allow video to fullscreen!\nError: ${err.name}\n${err.message}');
        });
    };
}