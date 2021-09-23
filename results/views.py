# Create your views here.

import os, datetime, math, logging, shutil
from django.shortcuts import render
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.template import RequestContext
from results.DataTypes import *
from results.Blocks import *
from results.models import SavedPipeline, ShortURL
from results.Pipeline import *
import results.PipelineEncoder
from plotty import settings

class LoggingStream(object):
    def __init__(self):
        self.entries = []
    def write(self, s):
        self.entries.append(s)
    def flush(self):
        pass
    def val(self):
        s = ""
        for l in self.entries:
            s += l + "\r\n"
        return s

def list(request, pipeline):
    log_stream = LoggingStream()
    stream_handler = logging.StreamHandler(log_stream)
    root_logger = logging.getLogger()
    root_logger.addHandler(stream_handler)

    try:
        #dt, graph_outputs = execute_pipeline(pipeline)
        p = Pipeline(web_client=False)
        p.decode(pipeline)
        graph_outputs = p.apply()
    except LogTabulateStarted as e:
        output = ''
        return HttpResponse("Tabulating: log %s, pid %d, log number %d/%d" % (e.log, e.pid, e.index, e.length))
    except PipelineBlockException as e:
        output = '<div class="exception"><h1>Exception in executing block ' + str(e.block + 1) + '</h1>' + e.msg
        output += '<h1>Traceback</h1><pre>' + e.traceback + '</pre><h1>Log</h1><pre>' + log_stream.val() + '</pre<</div>'
        return HttpResponse(output)
    except PipelineLoadException as e:
        output = '<div class="exception"><h1>Exception in loading log files</h1>' + e.msg
        output += '<h1>Traceback</h1><pre>' + e.traceback + '</pre><h1>Log</h1><pre>' + log_stream.val() + '</pre<</div>'
        return HttpResponse(output)
    except PipelineAmbiguityException as e:
        output = 'Ambiguity: ' + e.msg + ' in block ' + str(e.block)
        return HttpResponse(output)
    
    output = ''
    if len(graph_outputs) > 0:
        #for i, graph_set in enumerate(graph_outputs, start=1):
        #    for graph in graph_set:
        #        output += '<div class="foldable"><h1>' + graph['title'] + ' (block ' + str(i) + ')</h1>' + graph['hash'] + '</div>'
        output += '<div class="foldable"><h1>Table</h1>' + p.dataTable.renderToTable() + '</div>'
    else:
        output += p.dataTable.renderToTable()
    
    return HttpResponse('<html><head><title>Listing</title></head><body>' + output + '</body></html')

def pipeline(request):
    is_log_dir = lambda f: os.path.isdir(os.path.join(settings.BM_LOG_DIR, f)) and not f.endswith(".ca")
    is_csv_file = lambda f: os.path.isfile(os.path.join(settings.BM_LOG_DIR, f)) and f.endswith(".csv")
    logs = [f for f in os.listdir(settings.BM_LOG_DIR) if is_log_dir(f) or is_csv_file(f)]
    logs.sort(key=str.lower)
    pipelines = SavedPipeline.objects.all().order_by('name')
    return render(request, 'pipeline.html', {
        'logs': logs,
        'pipelines': pipelines,
        'debug': settings.DEBUG
    })

def shorturl(request, url):
    try:
        shorturlentry = ShortURL.objects.get(url=url)
    except ShortURL.DoesNotExist:
        return HttpResponse("Invalid short URL")
    #return HttpResponsePermanentRedirect('../#' + shorturlentry.encoded)
    # IE doesn't like 301/2 redirects with very long URLs :(
    return HttpResponse('<meta http-equiv="refresh" content="0; url=../#' + shorturlentry.encoded + '">')

def debug_clear_cache(request):
    path = os.path.join(settings.CACHE_ROOT, 'log/')
    shutil.rmtree(path)
    os.mkdir(path)
    return HttpResponse('Purged cache in ' + path)
