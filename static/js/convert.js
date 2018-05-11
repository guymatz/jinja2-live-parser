$(document).ready(function(){
    // console.log("poopy");
    $('#clear').click(function() {
        //$('#template').val('');
        $('#render').val('');
        //$('#values').val('');
        $('#render').html('');
    });

    // $('#use_json').click(function() {
    $('input[name=use_json]').change(function() {
        // console.log("poopy2");
        if($(this).is(':checked')) {
            $("#data h1").html("Pillar Data (JSON)");
        }
        else {
            $("#data h1").html("Pillar Data (YAML)");
        } 
    });

    $('#convert').click(function() {
        // console.log("poopy3");
        var is_checked_showwhitespaces = $('input[name="showwhitespaces"]').is(':checked') ? 1:0;
        var is_checked_dummyvalues = $('input[name="dummyvalues"]').is(':checked') ? 1:0;
        var is_checked_use_json = $('input[name="use_json"]').is(':checked') ? 1:0;
        var is_checked_use_remote_data = $('input[name="use_remote_data"]').is(':checked') ? 1:0;
        // console.log("poopy4");


        // Push the input to the Jinja2 api (Python)
        $.post('/convert', {
            template: $('#template').val(),
            values: $('#values').val(),
            showwhitespaces: is_checked_showwhitespaces,
            dummyvalues: is_checked_dummyvalues,
            use_json: is_checked_use_json,
            use_remote_data: is_checked_use_remote_data,
            remote_server: $('#remote_server').val(),
            remote_username: $('#remote_username').val(),
            remote_password: $('#remote_password').val()
        }).done(function(response) {
            // console.log("poopy5");
            // Grey out the white spaces chars if any
            response = response.replace(/•/g, '<span class="whitespace">•</span>');

            // Display the answer
            // console.log("poopy6");
            $('#render').html(response);
        });
    });
});
