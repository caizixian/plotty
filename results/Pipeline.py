import plotty.results.PipelineEncoder
from django.core.cache import cache
from django.db.models import Max
from plotty.results.DataTypes import DataTable, DataRow, DataAggregate, Messages
from plotty.results.Blocks import *
from plotty.results.Exceptions import *
import plotty.results.PipelineEncoder as PipelineEncoder
import sys, traceback, logging, copy, os, time

BLOCK_MAPPINGS = {
    '1': FilterBlock,
    '2': AggregateBlock,
    '3': NormaliseBlock,
    '4': GraphBlock,
    '5': ValueFilterBlock,
    '6': CompositeScenarioBlock,
    '7': FormatBlock,
    '8': LBOBlock
}

class Pipeline(object):
    """ A Pipeline consists of selected log files, selected scenario columns and
        value columns, and a set of blocks.

        This is distinct from DataTypes.DataTable. We wish to preserve the
        distinction between the Pipeline as a set of actions, and the DataTable
        which results from applying a Pipeline to a set of data. """

    FLAG_NOTHING = 0

    def __init__(self, web_client=False):
        self.timestamp = time.time()
        self.flags = 0
        self.logs = []
        self.scenarioCols = set()
        self.valueCols = set()
        self.derivedValueCols = set()
        self.blocks = []
        self.dataTable = None
        self.messages = None
        self.webClient = web_client
        # -1 means 'no cache available', 0 means 'before block 1' (i.e. only
        # the pipeline with 0 blocks), 1 means 'after block 1', etc
        self.cacheAvailableIndex = -1
        # The cache key to load from to replace the first cacheAvailableIndex
        # blocks
        self.cacheAvailableKey = ""
        self.cacheKeyBase = ""

    def decode(self, encoded):
        """ Decodes an entire paramater string. """
        try:
            parts = encoded.split(PipelineEncoder.BLOCK_SEPARATOR)
            # Flagword and pipeline-config are required
            if len(parts) < 2:
                raise PipelineError("Decode invalid because not enough parts")
            
            self.flags = int(parts[0])

            pipelineConfig = parts[1].split(PipelineEncoder.GROUP_SEPARATOR)
            # All four parts required - logs, scenarios, values, derivedVals (may be empty)
            if len(pipelineConfig) != 4:
                raise PipelineError("Decode invalid because not enough pipeline-config parts")
            
            self.logs = pipelineConfig[0].split(PipelineEncoder.PARAM_SEPARATOR)
            self.scenarioCols = set(pipelineConfig[1].split(PipelineEncoder.PARAM_SEPARATOR))
            self.valueCols = set(pipelineConfig[2].split(PipelineEncoder.PARAM_SEPARATOR))
            # Filter whitespace-only values
            self.derivedValueCols = set(filter(lambda x: x != '', pipelineConfig[3].split(PipelineEncoder.PARAM_SEPARATOR)))

            # Put the first two parts back into a string, to be used as a 
            # cache key
            # XXX TODO: we don't do anything sensible about sorting/order in
            # the paramater lists, that would make two different encoded strings
            # represent the same pipeline
            encoded_cumulative = PipelineEncoder.BLOCK_SEPARATOR.join(parts[0:2])
            self.cacheKeyBase = encoded_cumulative

            # Index 2 onwards are blocks
            for params in parts[2:]:
                if len(params.strip()) == 0:
                    continue
                encoded_cumulative += PipelineEncoder.BLOCK_SEPARATOR + params
                # Chomp the first character, the block ID
                block = BLOCK_MAPPINGS[params[0]]()
                block.decode(params[1:], encoded_cumulative)
                self.blocks.append((block, encoded_cumulative))
            
            # Now try to determine how late in the pipeline we can load from
            # an existing cache.
            # First, get a date to test with - if cached values are older than
            # the last modified date of the log file(s), we can't use them
            lastModified = 0
            for l in self.logs:
                mtime = os.path.getmtime(os.path.join(settings.BM_LOG_DIR, l))
                if mtime > lastModified:
                    lastModified = mtime


            usedFormats = [b.key for (b, ec) in self.blocks if isinstance(b, FormatBlock)]
            if len(usedFormats) > 0:
                lastModifiedFormat = FormatStyle.objects.filter(key__in=usedFormats).aggregate(Max('modified'))['modified__max']
                if lastModifiedFormat:
                    lastModifiedFormat = time.mktime(lastModifiedFormat.timetuple())
                    if (lastModifiedFormat > lastModified):
                        lastModified = lastModifiedFormat

            usedFormats = [b.format_key for (b, ec) in self.blocks if isinstance(b, GraphBlock)]
            if len(usedFormats) > 0:
                lastModifiedFormat = GraphFormat.objects.filter(key__in=usedFormats).aggregate(Max('modified'))['modified__max']
                if lastModifiedFormat:
                    lastModifiedFormat = time.mktime(lastModifiedFormat.timetuple())
                    if (lastModifiedFormat > lastModified):
                        lastModified = lastModifiedFormat

            # Now work backwards, checking where we can break into the
            # pipeline. 
            for idx in range(len(parts), 1, -1):
                possibleCacheKey = PipelineEncoder.BLOCK_SEPARATOR.join(parts[:idx])
                cacheValue = cache.get(possibleCacheKey)
                if cacheValue != None:
                    if cacheValue['last_modified'] >= lastModified:
                        logging.debug("Found partial result %s in the cache" % possibleCacheKey)
                        # Good cache value, let's use it
                        self.cacheAvailableKey = possibleCacheKey
                        self.cacheAvailableIndex = idx - 2 # Account for the first two chunks
                        break
                    else:
                        # Too old, clean it up
                        cache.delete(possibleCacheKey)


        except:
            raise PipelineLoadException(*sys.exc_info())
        
    def apply(self):
        if len(self.logs) == 0:
            raise PipelineError("No log files are selected.", 'selected log files')
        
        graph_outputs = []
        block_scenario_values = []
        block_scenario_display= []
        block_values = []
        block_values_display = []

        def extractValues(vs):
            return dict([(key, list([v.value if isinstance(v, ScenarioValue) else str(v) for v in vs[key]])) for key in vs.iterkeys()])

        def extractDisplay(vs):
            return dict([(key, list([v.display if isinstance(v, ScenarioValue) else str(v) for v in vs[key]])) for key in vs.iterkeys()])

        def extractValueDisplay(display, cols):
            return [v.display if isinstance(v, ScenarioValue) else str(v) for v in [display[x] for x in cols]]

        # Preempt the pipeline if necessary
        if self.cacheAvailableIndex > -1:
            cacheValue = cache.get(self.cacheAvailableKey)
            self.dataTable = cacheValue['data_table']
            self.messages = self.dataTable.messages
            graph_outputs = cacheValue['graph_outputs']
            block_scenario_values = cacheValue['block_scenario_values']
            block_scenario_display = cacheValue['block_scenario_display']
            block_values = cacheValue['block_values']
            block_values_display = cacheValue['block_values_display']
        else:
            try:
                self.dataTable = DataTable(logs=self.logs, wait=not self.webClient)
                self.messages = self.dataTable.messages

                # Values for the pipeline
                selectedValueCols = list(self.dataTable.valueColumns)
                selectedValueCols.sort()
                selectedScenarioCols = list(self.dataTable.scenarioColumns)
                selectedScenarioCols.sort()
                block_values.append(selectedValueCols)
                block_values_display.append(extractValueDisplay(self.dataTable.valueColumnsDisplay, selectedValueCols))
                scenarioValues = self.dataTable.getScenarioValues()
                block_scenario_values.append(extractValues(scenarioValues))
                block_scenario_display.append(extractDisplay(scenarioValues))

                # Values before the first block.
                self.dataTable.selectScenarioColumns(self.scenarioCols)
                self.dataTable.selectValueColumns(self.valueCols, self.derivedValueCols)
                selectedValueCols = list(self.dataTable.valueColumns)
                selectedValueCols.sort()
                selectedScenarioCols = list(self.dataTable.scenarioColumns)
                selectedScenarioCols.sort()
                block_values.append(selectedValueCols)
                block_values_display.append(extractValueDisplay(self.dataTable.valueColumnsDisplay, selectedValueCols))
                scenarioValues = self.dataTable.getScenarioValues()
                block_scenario_values.append(extractValues(scenarioValues))
                block_scenario_display.append(extractDisplay(scenarioValues))

                # Cache it
                cache.set(self.cacheKeyBase, {
                    'last_modified': self.timestamp,
                    'data_table': self.dataTable,
                    'block_values': block_values,
                    'block_values_display': block_values_display,
                    'block_scenario_values': block_scenario_values,
                    'block_scenario_display': block_scenario_display,
                    'graph_outputs': graph_outputs
                })
            except LogTabulateStarted:
                raise
            except PipelineAmbiguityException as e:
                e.block = 'selected data'
                e.block_values = block_values
                e.block_values_display = block_values_display
                e.block_scenario_values = block_scenario_values
                e.block_scenario_display = block_scenario_display
                raise e
            except PipelineError:
                raise
            except:
                raise PipelineLoadException(*sys.exc_info())

        # e.g. if cacheAvailableIndex = 2, we've already loaded the output up to
        # and including block 2, so the first block to run is block 3, but
        # self.blocks is zero-indexed, so the first index to run is 2
        firstBlockToRun = 0 if self.cacheAvailableIndex == -1 else self.cacheAvailableIndex
        for i,(block,cacheKey) in enumerate(self.blocks[firstBlockToRun:]):
            try:
                ret = block.apply(self.dataTable, self.messages)
            except PipelineAmbiguityException as e:
                e.block = i + firstBlockToRun
                # Remove this block + the rest of the pipeline, and try again
                # This is safe - if we've gotten to this point, everything
                # before this block has already worked
                del self.blocks[i+firstBlockToRun:]
                (block_scenario_values, block_scenario_display, block_values, block_values_display, graph_outputs) = self.apply()
                e.dataTable = self.dataTable
                e.messages = self.messages
                e.graph_outputs = graph_outputs
                e.block_values = block_values
                e.block_values_display = block_values_display
                e.block_scenario_values = block_scenario_values
                e.block_scenario_display = block_scenario_display
                raise e
            except PipelineError as e :
                e.block = i + firstBlockToRun
                # Remove this block + the rest of the pipeline, and try again
                # This is safe - if we've gotten to this point, everything
                # before this block has already worked
                del self.blocks[i+firstBlockToRun:]
                (block_scenario_values, block_scenario_display, block_values, block_values_display, graph_outputs) = self.apply()
                e.dataTable = self.dataTable
                e.messages = self.messages
                e.graph_outputs = graph_outputs
                e.block_values = block_values
                e.block_values_display = block_values_display
                e.block_scenario_values = block_scenario_values
                e.block_scenario_display = block_scenario_display
                raise e
            except:
                raise PipelineBlockException(i+firstBlockToRun, *sys.exc_info())
            
            if isinstance(block, GraphBlock):
                graph_outputs.append(ret)
            
            selectedValueCols = list(self.dataTable.valueColumns)
            selectedValueCols.sort()
            selectedScenarioCols = list(self.dataTable.scenarioColumns)
            selectedScenarioCols.sort()
            block_values.append(selectedValueCols)
            block_values_display.append(extractValueDisplay(self.dataTable.valueColumnsDisplay, selectedValueCols))
            scenarioValues = self.dataTable.getScenarioValues()
            block_scenario_values.append(extractValues(scenarioValues))
            block_scenario_display.append(extractDisplay(scenarioValues))

            # Cache it
            cache.set(cacheKey, {
                'last_modified': self.timestamp,
                'data_table': self.dataTable,
                'block_values': block_values,
                'block_values_display': block_values_display,
                'block_scenario_values': block_scenario_values,
                'block_scenario_display': block_scenario_display,
                'graph_outputs': graph_outputs
            })


        return (block_scenario_values, block_scenario_display, block_values, block_values_display, graph_outputs)
