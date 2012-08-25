$(document).ready(function() {
    configurar_formulario_filtro();
    conectar_indicador_actividad();
    $('#keyword').focus()
});


function configurar_formulario_filtro() {
    $("#form").bind('submit',function(){
        var $keyword = $('#keyword');
        limpiar_filtros();
        if ($.trim($keyword.val()).length != 0) {
            actualizar_filtros($keyword.val());
        }
        return false;
    });
}


function conectar_indicador_actividad() {
    $(document).ajaxStart(function() {
        $('#keyword').addClass('working');
    });
    $(document).ajaxStop(function() {
        $('#keyword').removeClass('working');
    });
}


function limpiar_filtros() {
    $('#regex_table tbody').html('');
    $('#xquery_table tbody').html('');
}


function actualizar_filtros(keyword) {
    actualizar_filtro_regex(keyword);
    actualizar_filtro_xquery(keyword);
}


function actualizar_filtro_regex(keyword) {
    $.getJSON('/filtro_regex/?', {'q':keyword}, function(data) {
        var items = [];
        var titles = data.titles
        $.each(titles, function(index) {
            items.push('<tr><td>' + titles[index] + '</td></tr>');
        });
        $('#regex_table tbody').html(items.join(''));
    });
}


function actualizar_filtro_xquery(keyword) {
    $.get('/filtro_xquery/?', {'q':keyword}, function(data) {
        $('#xquery_table tbody').html(data);
    });
}
