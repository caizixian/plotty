if ( typeof console === 'undefined' ) {
    var console = {
        log: function() {}
    }
}
if ( typeof Array.prototype.map === 'undefined' ) {
    Array.prototype.map = function(func, context) {
        var newList = [];
        for ( var i = 0; i < this.length; i++ ) {
            newList.push(func.call(context, this[i]));
        }
        return newList;
    }
}

// Adds a distinct number to every normalise block to make sure the radio
// buttons toggle around correctly
var normaliseBlockCount = 0;

var PipelineEncoder = {
    /*
     * Constants
     */
    
    BLOCK_SEPARATOR: '|',
    GROUP_SEPARATOR: '&',
    
    AGGREGATE_TYPES: { 0: 'mean',
                       1: 'geomean' },
    
    FILTER_PARAM_SEPARATOR: '^',
    
    BLOCK_IDS: { 0: 'filter',
                 1: 'aggregate',
                 2: 'normalise',
                 3: 'graph' },
    
    
    /*
     * Init
     */
    hasInited: false,
    
    init: function() {
        this.BLOCK_DECODES = { 0: this.decode_filter_block,
                               1: this.decode_aggregate_block,
                               2: this.decode_normalise_block,
                               3: this.decode_graph_block };
        this.BLOCK_ENCODES = { 'filter': this.encode_filter_block,
                               'aggregate': this.encode_aggregate_block,
                               'normalise': this.encode_normalise_block,
                               'graph': this.encode_graph_block };
        this.hasInited = true;
    },
    
    /*
     * Misc
     */
    reverse_dict_lookup: function(dict, lookup) {
        for ( var j in dict )
            if ( dict[j] == lookup )
                return j;
        return null;
    },
    
    /*
     * Decoding routines
     */
    decode_pipeline: function(data) {
        if ( !this.hasInited )
            this.init();
        var chunks = data.split(this.BLOCK_SEPARATOR);
        var scenario_columns = chunks[1].split(this.GROUP_SEPARATOR);
        var value_columns = chunks[2].split(this.GROUP_SEPARATOR);
        var selected_logs = chunks[0].split(this.GROUP_SEPARATOR);
        return {'logs': selected_logs, 'scenario_columns': scenario_columns, 'value_columns': value_columns, 'blocks': chunks.slice(3).map(this.decode_pipeline_block, this)};
    },
    
    decode_pipeline_block: function(data) {
        var type = parseInt(data[0]);
        return this.BLOCK_DECODES[type].call(this, data.substr(1));
    },
    
    decode_filter_block: function(data) {
        var filter_strings = data.split(this.GROUP_SEPARATOR);
        var filters = [];
        for ( var i = 0; i < filter_strings.length; i++ ) {
            var split = filter_strings[i].split(this.FILTER_PARAM_SEPARATOR);
            var filter_dict = {'column': split[0], 'value': split[2]};
            if ( split[1] == '0' )
                filter_dict['is'] = false;
            else
                filter_dict['is'] = true;
            filters.push(filter_dict);
        }
        return {'type': 'filter', 'filters': filters};
    },
    
    decode_aggregate_block: function(data) {
        var params_string = data.split(this.GROUP_SEPARATOR);
        return {'type': 'aggregate', 'params': {'column': params_string[0], 'type': this.AGGREGATE_TYPES[parseInt(params_string[1])]}};
    },
    
    decode_normalise_block: function(data) {
        var params_string = data.split(this.GROUP_SEPARATOR);
        if ( params_string[0] == '0' )
            return {'type': 'normalise', 'params': {'normaliser': 'select', 'column': params_string[1], 'value': params_string[2]}};
        else if ( params_string[0] == '1' )
            return {'type': 'normalise', 'params': {'normaliser': 'best', 'group': params_string.slice(1)}};
    },
    
    decode_graph_block: function(data) {
        return {'type': 'graph'};
    },

    
    /*
     * Encoding routines
     */
    encode_pipeline: function(data) {
        if ( !this.hasInited )
            this.init();
        return [data['logs'].join(this.GROUP_SEPARATOR), data['scenario_columns'].join(this.GROUP_SEPARATOR), data['value_columns'].join(this.GROUP_SEPARATOR)].concat(data['blocks'].map(this.encode_pipeline_block, this)).join(this.BLOCK_SEPARATOR);
    },
    
    encode_pipeline_block: function(data) {
        return this.reverse_dict_lookup(this.BLOCK_IDS, data['type']) + this.BLOCK_ENCODES[data['type']].call(this, data);
    },
    
    encode_filter_block: function(data) {
        var filter_strings = [];
        for ( var i = 0; i < data['filters'].length; i++ ) {
            var is_type;
            if ( data['filters'][i]['is'] )
                is_type = '1';
            else
                is_type = '0';
            filter_strings.push([data['filters'][i]['column'], is_type, data['filters'][i]['value']].join(this.FILTER_PARAM_SEPARATOR));
        }
        return filter_strings.join(this.GROUP_SEPARATOR);
    },
    
    encode_aggregate_block: function(data) {
        return [data['params']['column'], this.reverse_dict_lookup(this.AGGREGATE_TYPES, data['params']['type'])].join(this.GROUP_SEPARATOR);
    },
    
    encode_normalise_block: function(data) {
        if ( data['params']['normaliser'] == 'select' )
            return ['0', data['params']['column'], data['params']['value']].join(this.GROUP_SEPARATOR);
        else
            return ['1', data['params']['group'].join(this.GROUP_SEPARATOR)].join(this.GROUP_SEPARATOR);
    },
    
    encode_graph_block: function(data) {
        return '';
    }
}

function addBlock(type) {
	var newBlock = $('#pipeline-' + type + '-template').clone();
	newBlock.attr('id', '');
	
	if ( type == 'normalise' ) {
	    $('input:radio', newBlock).attr('name', 'normalise-type-' + normaliseBlockCount).first().attr('checked', 'checked');
	    $('.select-normalise-group').attr('name', 'normalise-group-' + normaliseBlockCount);
	    normaliseBlockCount++;
    }
	    
	newBlock.insertBefore('#pipeline-add');
}

function updateAddRemoveButtons(table) {
    var rows = $('tr', table);
    if ( rows.length > 1 ) {
        /*rows.each(function(i) {
            $('.remove-row', this).attr('disabled', '');
            $('.add-row', this).css('display', 'none');
        });*/
        $('.remove-row', rows).attr('disabled', '');
        $('.add-row', rows).css('display', 'none');
    }
    else {
        $('.remove-row', rows).attr('disabled', 'disabled');
    }
    $('tr:last-child .add-row', table).css('display', 'block');
}

function addBlockTableRow(button) {
    var table = $(button).parents('table');
    var newRow = $('tr:first-child', table).clone();
    
    $('select', newRow).each(function() {
        this.selectedIndex = 0;
    });
    
    $(table).append(newRow);
    
    updateAddRemoveButtons(table);
}

function removeBlockTableRow(button) {
    var table = $(button).parents('table');
    $(button).parents('tr').remove();
    updateAddRemoveButtons(table);
}

function updateAvailableColumns(data) {
    console.log('updateAvailableColumns: ', data);
    $('.scenario-column').each(function() {
        var oldValue = $(this).val();
        this.options.length = 0;
        this.options.add(new Option("[" + data.scenarioCols.length + " options]", ''));
        for ( var i = 0; i < data.scenarioCols.length; i++ ) {
            this.options.add(new Option(data.scenarioCols[i], data.scenarioCols[i]));
            if ( data.scenarioCols[i] == oldValue )
                this.options.selectedIndex = i+1;
        }
    });
    
    updateMultiSelect('#select-scenario-cols, .select-normalise-group', data.scenarioCols, true);
    updateMultiSelect('#select-value-cols', data.valueCols, false);
}

/* It's much easier to throw out the old multi-select and build a new one
 * when we need to update the available values, when we're using the checkbox
 * plugin. */
function updateMultiSelect(selector, vals, considerSelectAll) {
    // Get the old selections
    $(selector).each(function() {
        var selection = $(this).val() || [];
        var selectAll = false;
        if ( considerSelectAll && (selection.length == $(this).children('input').length || selection.length == 0) )
            selectAll = true;
        
        // Build a new select
        var dropdown = document.createElement('select');
        dropdown.multiple = "multiple";
        for ( var i = 0; i < vals.length; i++ )
            dropdown.options.add(new Option(vals[i], vals[i]));
        if ( selectAll || selection.length > 0 )
            for ( var i = 0; i < vals.length; i++ )
                if ( selectAll || jQuery.inArray(dropdown.options[i].value, selection) > -1 )
                    dropdown.options[i].selected = true;
                    
        dropdown.id = $(this).attr('id');
        dropdown.name = $(this).attr('name');
        dropdown.className = $(this).attr('class');
        //dropdown.style.width = "100%";
        
        // Replace the old select
        $(this).replaceWith(dropdown);
    });

    // Transform only the visible ones (we can't transform the invisible ones
    // until they show up otherwise the dimensions are broken)
    $(selector).filter(':visible').toChecklist();
}

function updateAvailableValues(vals) {
    console.log('updateAvailableValues: ', vals, ' for dropdown: ', this);
    this.options.length = 0;
    this.options.add(new Option("[" + vals.length + " options]", '', true));
    for ( var i = 0; i < vals.length; i++ ) {
        this.options.add(new Option(vals[i], vals[i]));
    }
}

function selectedLogFiles() {
    var logs = [];
    var log_selects = $('.select-log').get();
    for ( var i = 0; i < log_selects.length; i++ ) {
        logs.push($(log_selects[i]).val());
    }
    return logs;
}

function serialisePipeline() {
    var dict = {}
    dict['logs'] = selectedLogFiles();
    dict['scenario_columns'] = $('#select-scenario-cols').val();
    dict['value_columns'] = $('#select-value-cols').val();
    
    if ( dict['scenario_columns'].length == 0 || dict['value_columns'].length == 0 )
        return false;
    
    var blocks = [];
    var throwInvalid = false;
    if ( $('#pipeline .pipeline-block').length == 0 )
        return false;
    $('#pipeline .pipeline-block').each(function() {
        if ( $(this).hasClass('filter') ) {
            var filters = []
            $('tr', this).each(function() {
                var is;
                if ( $('.select-filter-is', this).val() == 'is' )
                    is = true;
                else
                    is = false;
                var column = $('.select-filter-column', this).val();
                var value = $('.select-filter-value', this).val();
                if ( column == '' || value == '' ) {
                    throwInvalid = true;
                    return false;
                }
                filters.push({'column': column, 'is': is, 'value': value});
            });
            blocks.push({'type': 'filter', 'filters': filters});
        }
        else if ( $(this).hasClass('aggregate') ) {
            var column = $('.select-aggregate-column', this).val();
            var type = $('.select-aggregate-type', this).val();
            if ( column == '' || type == '' ) {
                throwInvalid = true;
                return false;
            }
            blocks.push({'type': 'aggregate', 'params': {'column': column, 'type': type}});
        }
        else if ( $(this).hasClass('normalise') ) {
            var selected_type = $('input:radio:checked', this);
            if ( selected_type.val() == 'select' ) {
                var column = $('.select-normalise-column', this).val();
                var value = $('.select-normalise-value', this).val();
                if ( column == '' || value == '' ) {
                    throwInvalid = true;
                    return false;
                }
                blocks.push({'type': 'normalise', 'params': {'normaliser': 'select', 'column': column, 'value': value}});
            }
            else if ( selected_type.val() == 'best' ) {
                var group = $('.select-normalise-group', this).val();
                /*if ( group.length == 0 ) {
                    throwInvalid = true;
                    return false;
                }*/
                blocks.push({'type': 'normalise', 'params': {'normaliser': 'best', 'group': group}});
            }
            else {
                console.log('val = ' + selected_type.val());
                throwInvalid = true;
                return false;
            }
        }
        else if ( $(this).hasClass('graph') ) {
            blocks.push({'type': 'graph'});
        }
        if ( throwInvalid )
            return false;
    });
    if ( throwInvalid )
        return false;
    dict['blocks'] = blocks;
    return dict;
}

function refreshPipeline() {
    console.log('refreshPipeline()');
    var pipeline = serialisePipeline();
    if ( pipeline ) {
        var encoded = PipelineEncoder.encode_pipeline(pipeline);
        console.log('Loading pipeline: ' + encoded);
        $('#pipeline-debug-link').attr('href', 'list/' + encoded);
        $.get('/results/ajax/pipeline/' + encoded, function(data) {
            $('#output table').remove();
            $('#output').append(data);
            $('#output table').tablesorter();
        });
    }
    else if ( $('#pipeline .pipeline-block').length == 0 ) {
        $('#output table').remove();
    }
}

$(document).ready(function() {
    $.ajaxSetup({
        cache: false
    });
    $(document).ajaxStart(function() {
        $('#loading-indicator').css({visibility: 'visible'});
    });
    $(document).ajaxStop(function() {
        $('#loading-indicator').css({visibility: 'hidden'});
    });
	$("#add-filter").click(function() {
		addBlock('filter');
	});
	$("#add-aggregate").click(function() {
		addBlock('aggregate');
	});
	$("#add-normalise").click(function() {
		addBlock('normalise');
	});
	$("#add-graph").click(function() {
		addBlock('graph');
	});
	$(".remove-button").live('click', function() {
		$(this).parent().remove();
		refreshPipeline();
	});
	$(".add-row").live('click', function() {
	    addBlockTableRow(this);
	});
	$(".remove-row").live('click', function() {
	    if ( this.disabled === true ) return; // This is the silliest IE bug ever
	    removeBlockTableRow(this);
	    refreshPipeline();
	});
	$("#pipeline-log").delegate(".select-log", 'change', function() {
	    $.getJSON('/results/ajax/log-values/' + selectedLogFiles().join(',') + '/', updateAvailableColumns);
	});
	$("#pipeline").delegate(".select-filter-column", 'change', function() {
	    var values_select = $('.select-filter-value', $(this).parents('tr')).get(0);
	    $.ajax({
	        context: values_select,
	        dataType: 'json',
	        url: '/results/ajax/filter-values/' + selectedLogFiles().join(',') + '/' + $(this).val() + '/',
	        success: updateAvailableValues
	    });
	});
	$("#pipeline").delegate(".select-normalise-column", 'change', function() {
	    var values_select = $('.select-normalise-value', $(this).parent()).get(0);
	    $.ajax({
	        context: values_select,
	        dataType: 'json',
	        url: '/results/ajax/filter-values/' + selectedLogFiles().join(',') + '/' + $(this).val() + '/',
	        success: updateAvailableValues
	    });
	});
	$("#pipeline-values").delegate("#select-scenario-cols input", 'change', function() {
	    var selected = $(this).parents("#select-scenario-cols").val() || [];
	    $('.scenario-column').each(function() {
	        var oldValue = $(this).val();
            this.options.length = 0;
            this.options.add(new Option("[" + selected.length + " options]", ''));
            for ( var i = 0; i < selected.length; i++ ) {
                this.options.add(new Option(selected[i], selected[i]));
                if ( selected[i] == oldValue )
                    this.options.selectedIndex = i+1;
            }
	    });
	    refreshPipeline();
	});
	$("#pipeline-values").delegate("#select-value-cols input", 'change', function() {
	    refreshPipeline();
	});
	$("#pipeline").delegate("input:radio", 'change', function() {
	    var group_select = $('.normalise-group', $(this).parents(".pipeline"));
	    if ( this.checked == true && this.value == 'select' ) {
	        group_select.css('display', 'none');
	        $('select', $(this).parents(".pipeline")).attr('disabled', '');
        }
	    else if ( this.checked == true && this.value == 'best' ) {
	        group_select.css('display', 'block');
	        if ( $('select', group_select).length > 0 ) {
	            $('select', group_select).toChecklist();
	            $(this).parents(".pipeline").delegate(".select-normalise-group input", 'change', function() {
	                refreshPipeline();
	            });
            }
	        $('select', $(this).parents(".pipeline")).attr('disabled', 'disabled');
	        refreshPipeline();
        }
	});
	$("#select-scenario-cols, #select-value-cols").toChecklist();
	
	$("#pipeline").delegate('select', 'change', refreshPipeline);
});
