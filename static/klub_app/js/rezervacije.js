document.addEventListener('DOMContentLoaded', function() {
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridWeek',
        events: '/rezervacije/json/',
        eventContent: function(arg) {
            var count = arg.event.extendedProps.count || 1;
            var color = count >= 6 ? '#ff4d4d' : count > 0 ? '#add8e6' : '#ffffff';
            return { html: '<div style="background-color:' + color + '; padding:2px; border-radius:3px;">' + arg.event.title + '</div>' };
        },
        dateClick: function(info) {
            var datum = info.dateStr;
            fetchReservations(datum);
        },
        eventClick: function(info) {
            if (confirm('Da li želite da otkažete rezervaciju za ' + info.event.title + '?')) {
                $.get('/rezervacije/brisi/' + info.event.id + '/', function() {
                    location.reload();
                });
            }
        }
    });
    calendar.render();

    function fetchReservations(datum) {
        $.get('/rezervacije/json/', function(data) {
            var $popup = $('#popup');
            var $clanSelect = $('#clanSelect');
            $clanSelect.empty();
            $.get('/rezervacije/json/clanovi/', function(clanovi) {
                clanovi.forEach(function(clan) {
                    $clanSelect.append(new Option(clan.ime_prezime, clan.id));
                });
                var reserved = data.filter(r => r.start.startsWith(datum)).map(r => r.title);
                if (reserved.length) {
                    alert('Već rezervisano za: ' + reserved.join(', '));
                } else {
                    $popup.data('datum', datum).show();
                }
            });
        });
    }

    $('#popup button').click(function() {
        var clan_id = $('#clanSelect').val();
        var sat = $('#satInput').val();
        var datum = $('#popup').data('datum');
        if (clan_id && sat && datum) {
            $.post('/rezervacije/', {
                clan_id: clan_id,
                datum: datum,
                sat: sat
            }, function() {
                location.reload();
            }).fail(function() {
                alert('Greška prilikom zakazivanja!');
            });
        }
        $('#popup').hide();
    });

    $(document).click(function(e) {
        if (!$(e.target).closest('#popup').length) {
            $('#popup').hide();
        }
    });
});