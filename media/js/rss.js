$(document).ready(function() {
  $("#form").bind('submit',function(){
    filter_feed_regex($("#keyword").val());
    filter_feed_xquery($("#keyword").val());
    return false;
  });
});


function filter_feed_regex(keyword) {
  $.getJSON('http://127.0.0.1:8000/filtro_regex/?', {'q':keyword}, function(data) {
    var items = [];
    var titles = data.titles
    $.each(titles, function(index) {
      items.push('<tr><td>' + titles[index] + '</td></tr>');
    });
    $('#regex_table tbody').html(items.join(''));
});
}


function filter_feed_xquery(keyword) {
  $.get('http://127.0.0.1:8000/filtro_xquery/?', {'q':keyword}, function(data) {
    /*var items = [];
    var news = data.news
    $.each(news, function(index) {
      items.push(news[index])
    });
    */
    $('#xquery_table tbody').html(data);
});
}
