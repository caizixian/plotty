from django.conf.urls import url
from django.conf import settings
from django.views.static import serve
from results import views, views_ajax
import os

urlpatterns = [
    url(r'^static/(?P<path>.*)$', serve, {'document_root': os.path.join(os.path.dirname(__file__), 'static')}),
    url(r'^graph/(?P<path>.*)$', serve, {'document_root': settings.GRAPH_CACHE_DIR}),
    url(r'^p/(?P<url>[A-Za-z0-9]{6})$', views.shorturl),

    #url(r'^ajax/log-values/(?P<logs>.*)/$', views_ajax.log_values),    
    #url(r'^ajax/filter-values/(?P<logs>.*)/(?P<col>.*)/$', views_ajax.filter_values),
    url(r'^ajax/pipeline/(?P<pipeline>.*)$', views_ajax.pipeline),
    url(r'^ajax/save-pipeline/$', views_ajax.save_pipeline),
    url(r'^ajax/delete-pipeline/$', views_ajax.delete_saved_pipeline),
    url(r'^ajax/create-shorturl/$', views_ajax.create_shorturl),
    url(r'^ajax/load-formatstyle/(?P<key>.*)/$', views_ajax.load_formatstyle),
    url(r'^ajax/save-formatstyle/(?P<key>.*)/$', views_ajax.save_formatstyle),
    url(r'^ajax/delete-formatstyle/(?P<key>.*)/$', views_ajax.delete_formatstyle),
    url(r'^ajax/load-graphformat/(?P<key>.*)/$', views_ajax.load_graphformat),
    url(r'^ajax/save-graphformat/(?P<key>.*)/$', views_ajax.save_graphformat),
    url(r'^ajax/delete-graphformat/(?P<key>.*)/$', views_ajax.delete_graphformat),
    url(r'^ajax/purge-cache/$', views_ajax.purge_cache),
    url(r'^ajax/reinstall-defaults/$', views_ajax.reinstall_defaults),
    #url(r'^ajax/pipeline-csv-table/(?P<pipeline>.*)$', views_ajax.csv_table),
    #url(r'^ajax/pipeline-csv-graph/(?P<pipeline>.*)/(?P<index>.*)/(?P<graph>.*)/$', views_ajax.csv_graph),
    url(r'^ajax/tabulate-progress/(?P<pid>[0-9]*)/$', views_ajax.tabulate_progress),
    
    # Debugging
    url(r'^list/graph/(?P<path>.*)$', serve, {'document_root': settings.GRAPH_CACHE_DIR}),
    url(r'^list/(?P<pipeline>.*)$', views.list),
    url(r'^debug-clear-cache/$', views.debug_clear_cache),

    url(r'', views.pipeline),
]
