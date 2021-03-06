
function each(array, fn) {
    for (
        var i = 0;
        i < array.length;
        ++i
    ) {
        fn(array[i], i)
    }
}

colour_map = []
function compute_colour_map() {
    var i;
    with (Math) {
        for (i = -500; i < 900; i++) {
            var x = i/1000 * PI
            var red = floor(sin(x) * 255)
            var green = floor(sin(x + (PI/3)) *255)
            var blue = floor(sin(x + (2 * PI/3)) *255)
            colour_map.push([
                red < 0 ? 0 : red,
                green < 0 ? 0 : green,
                blue < 0 ? 0 : blue
            ])
        }
    }
    return 
    // blue to cyan
    for (i = 0; i < 256; i++) {
        colour_map.push([0x0, i, 0xff])
    }

    // cyan to green
    for (i = 254; i >= 0; --i) {
        colour_map.push([0x0, 0xff, i])
    }

    // green to yellow
    for (i = 0; i < 256; i++) {
        colour_map.push([i, 0xff, 0x0])
    }

    // yellow to red
    for (i = 254; i >= 0; --i) {
        colour_map.push([0xff, i, 0x0])
    }
}
compute_colour_map()


function base64_encode (s) {
    var base64chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'.split("");
    var r = ""; 
    var p = ""; 
    var c = s.length % 3;
    if (c > 0) { 
        for (; c < 3; c++) { 
              p += '='; 
              s += "\0"; 
        } 
    }
    for (c = 0; c < s.length; c += 3) {
        if (c > 0 && (c / 3 * 4) % 76 == 0) { 
            r += "\r\n"; 
        }
        var n = (s.charCodeAt(c) << 16) + (s.charCodeAt(c+1) << 8) + s.charCodeAt(c+2);
        n = [(n >>> 18) & 63, (n >>> 12) & 63, (n >>> 6) & 63, n & 63];
        r += base64chars[n[0]] + base64chars[n[1]] + base64chars[n[2]] + base64chars[n[3]];
    }
    return r.substring(0, r.length - p.length) + p;
}
function createBmp(grid) {
    var bitmapFileHeader = 'BMxxxx\0\0\0\0yyyy';
    function multiByteEncode_(number, bytes) {
      var oldbase = 1
      var string = ''
      for (var x = 0; x < bytes; x++) {
        var byte = 0
        if (number != 0) {
          var base = oldbase * 256
          byte = number % base
          number = number - byte
          byte = byte / oldbase
          oldbase = base
        }
        string += String.fromCharCode(byte)
      }
      return string
    }
    var width = colour_map.length;

    var data = [];
    for (var x = 0; x < width; x++) {
        var value = colour_map[Math.floor((x/width) * colour_map.length)]
        data.push(
            String.fromCharCode(
                value[2],
                value[1],
                value[0]
            )
        )
    }
    padding = (
        width % 4 ? 
        '\0\0\0'.substr((width % 4) - 1, 3):
        ''
    );
    data.push(padding + padding + padding)
    var data_bytes = data.join('')

    var bitmapInfoHeader = 
        multiByteEncode_(40, 4) + // Number of bytes in the DIB header (from this point)
        multiByteEncode_(width, 4) + // Width of the bitmap in pixels
        multiByteEncode_(1, 4) + // Height of the bitmap in pixels
        '\x01\0' + // Number of color planes being used
        multiByteEncode_(24, 2) + // Number of bits per pixel
        '\0\0\0\0'+ // BI_RGB, no Pixel Array compression used
        multiByteEncode_(data_bytes.length, 4)+ // Size of the raw data in the Pixel Array (including padding)
        multiByteEncode_(2835, 4)+ //Horizontal resolution of the image
        multiByteEncode_(2835, 4)+ // Vertical resolution of the image
        '\0\0\0\0\0\0\0\0';

    var bitmap = bitmapFileHeader + bitmapInfoHeader + data_bytes
    bitmap = bitmap.replace(/yyyy/, multiByteEncode_(
      bitmapFileHeader.length + bitmapInfoHeader.length, 4))
    bitmap = bitmap.replace(/xxxx/, multiByteEncode_(bitmap.length, 4))
    return bitmap
};

function Vector(geometry, attributes, style) {
    style.strokeColor= 'none'
    style.fillOpacity= 0.8
    style.strokeWidth = 1

    return new OpenLayers.Feature.Vector(
        geometry, attributes, style
    )
}
function Polygon(components) {
    return new OpenLayers.Geometry.Polygon(components)
}
function Point(lon, lat) {
    var point = new OpenLayers.Geometry.Point(lat, lon)
    return point.transform(
        S3.gis.proj4326,
        S3.gis.projection_current
    )
}
function LinearRing(point_list) {
    point_list.push(point_list[0])
    return new OpenLayers.Geometry.LinearRing(point_list)
}


ClimateDataMapPlugin = function (config) {
    var plugin = this // let's be explicit!
    plugin.data_type_option_names = config.data_type_option_names
    plugin.parameter_names = config.parameter_names
    plugin.aggregation_names = config.aggregation_names
    plugin.year_min = config.year_min 
    plugin.year_max = config.year_max

    plugin.data_type_label = config.data_type_label
    plugin.overlay_data_URL = config.overlay_data_URL
    plugin.places_URL = config.places_URL
    plugin.chart_URL = config.chart_URL
    plugin.data_URL = config.data_URL
    
    plugin.chart_popup_URL = config.chart_popup_URL
    plugin.buy_data_popup_URL = config.buy_data_popup_URL
            
    delete config
    
    plugin.last_query_expression = null
    
    var initial_query_expression = (
        plugin.aggregation_names[0]+'('+
            '\n    "'+//form_values.data_type+' '+
            plugin.parameter_names[0].replace(new RegExp('\\+','g'),' ')+'",'+
            '\n    FromDate('+plugin.year_min+'),'+
            '\n    ToDate('+plugin.year_max+')'+
        '\n)'
    )
    plugin.places = {}
    var months = [
        '', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ]

    plugin.setup = function () {
        var overlay_layer = plugin.overlay_layer = new OpenLayers.Layer.Vector(
            'Filter',
            {
                isBaseLayer:false,                                
            }
        );
        map.addLayer(overlay_layer)
        // hovering over a square pops up a detail box
        function onFeatureSelect(feature) {
            var info = [
                // popup is styled with div.olPopup
                '<div class="place_info_popup">', 
                'value: ', feature.attributes.value, '<br />'
                //'</li>'
            ]
            var place = plugin.places[feature.attributes.place_id]
            if (!!place) {
                for (var p in place) {
                    if (place.hasOwnProperty(p)) {
                        value = place[p]
                        if (!!value) {
                            info.push(
                                //'<li>',
                                p,': ', value,
                                //'</li>'
                                '<br />'
                            )
                        }
                    }
                }
            }
            info.push('</div>')
            var popup = new OpenLayers.Popup(
                'info_bubble', 
                feature.geometry.getBounds().getCenterLonLat(),
                new OpenLayers.Size(170, 125),
                info.join(''),
                true
            )
            feature.popup = popup
            map.addPopup(popup)
        }
        function onFeatureUnselect(feature) {
            map.removePopup(feature.popup);
            feature.popup.destroy();
            feature.popup = null;
        }
        var hoverControl = new OpenLayers.Control.SelectFeature(
            overlay_layer,
            {
                title: 'Show detail by hovering over a square',
                hover: true,
                onSelect: onFeatureSelect,
                onUnselect: onFeatureUnselect
            }
        )
        map.addControl(hoverControl)
        hoverControl.activate()

        // selection
        OpenLayers.Feature.Vector.style['default']['strokeWidth'] = '2'
        var selectCtrl = new OpenLayers.Control.SelectFeature(
            overlay_layer,
            {
                clickout: true,
                toggle: false,
                toggleKey: 'altKey',
                multiple: false,
                multipleKey: 'shiftKey',
                hover: false,
                box: true,
                onSelect: function (feature) {
                    feature.style.strokeColor = 'black'
                    feature.style.strokeDashstyle = 'dash'
                    overlay_layer.drawFeature(feature)
                    plugin.show_chart_button.enable()
                },
                onUnselect: function (feature) {
                    // This doesn't always get called, even when the feature
                    // is unselected. Tried using setTimeout, no joy.
                    feature.style.strokeColor = 'none'
                    overlay_layer.drawFeature(feature)
                    if (plugin.overlay_layer.selectedFeatures.length == 0) {
                        plugin.show_chart_button.disable()
                    }
                }
            }
        )
                
        map.addControl(selectCtrl)

        selectCtrl.activate()
        $.ajax({
            url: plugin.places_URL,
            dataType: 'json',
            success: function (places_data) {
                each(
                    places_data,
                    function (place_data_pair) {
                        plugin.places[place_data_pair[0]] = place_data_pair[1]
                    }
                )
                plugin.update_map_layer(initial_query_expression)
            },
            error: function (jqXHR, textStatus, errorThrown) {
                plugin.set_status(
                    '<a target= "_blank" href="places">Could not load place data!</a>'
                )
            }
        })
        // make room by closing the layer tree
        setTimeout(
            function () {
                S3.gis.layerTree.collapse()
                $('#key_colour_scale').attr(
                    'src',
                    'data:image/bmp;base64,'+
                    base64_encode(createBmp())
                )
            },
            1000
        )
    }
    
    plugin.update_map_layer = function (
        query_expression
    ) {
        // request new features
        plugin.overlay_layer.destroyFeatures()
        plugin.set_status('Updating...')
        $('#freeform_query_textarea').text(query_expression)
        function done() {
            plugin.set_status('')
        }
        $.ajax({
            url: plugin.overlay_data_URL,
            dataType: 'json',
            data: {
                query_expression: query_expression
            },
            //timeout: 1000 * 20, // timeout doesn't seem to work
            success: function(feature_data, status_code) {
                if (feature_data.length == 0) {
                    plugin.set_status(
                        'No data for this selection. Has it been imported?'
                    )
                } else {                        
                    var place_ids = feature_data.keys
                    var values = feature_data.values
                    var units = feature_data.units
                    var converter = ({
                        "Kelvin": function (value) { return value - 273.16 },
                    }[units]) || function (x) { return x }
                    var display_units = ({
                        "Kelvin": "&#176;C",
                        "Δ Kelvin": "Δ &#176;C"
                    }[units]) || units
                    
                    var max_value = converter(Math.max.apply(null, values))
                    var min_value = converter(Math.min.apply(null, values))
                    
                    // sensible range
                    var significant_digits = 2
                    function scaling_factor(value) {
                        return 10.0^(
                            Math.floor(
                                Math.log(Math.abs(value)) / Math.LN10
                            ) - (significant_digits - 1)
                        )
                    }
                    function sensible(value, round) {
                        if (value == 0.0) {
                            return 0.0
                        }
                        else {
                            factor = scaling_factor(value)
                            return round(value/factor) * factor
                        }
                    }
                    range_mag = scaling_factor(
                        sensible(max_value, Math.ceil) - 
                        sensible(min_value, Math.floor)
                    )
                        
                   // function set_scale(min_value, max_value) {
                        min_value = Math.floor(min_value/range_mag) * range_mag
                        max_value = Math.ceil(max_value/range_mag) * range_mag
                        var range = max_value - min_value
                        
                        var features = []
                        for (
                            var i = 0;
                            i < place_ids.length;
                            i++
                        ) {
                            var place_id = place_ids[i]
                            var value = values[i]
                            var place = plugin.places[place_id]
                            var lat = place.latitude
                            var lon = place.longitude
                            north = lat + 0.05
                            south = lat - 0.05
                            east = lon + 0.05
                            west = lon - 0.05
                            var converted_value = converter(value)
                            var normalised_value = (converted_value - min_value) / range
                            if ((0.0 < normalised_value) && (normalised_value < 1.0)) {
                                var colour_value = colour_map[Math.floor(
                                    normalised_value * colour_map.length
                                )]
                                console.log(""+normalised_value+" "+value)
                                var colour_string = (
                                    '#'+
                                    (256+colour_value[0]).toString(16).substr(-2)+
                                    (256+colour_value[1]).toString(16).substr(-2)+
                                    (256+colour_value[2]).toString(16).substr(-2)
                                )
                                features.push(                            
                                    Vector(
                                        Polygon([
                                            LinearRing([
                                                Point(north,west),
                                                Point(north,east),
                                                Point(south,east),
                                                Point(south,west)
                                            ])
                                        ]),
                                        {
                                            value: converted_value.toPrecision(3)+" "+display_units,
                                            id: id,
                                            place_id: place_id
                                        },
                                        {
                                            fillColor: colour_string
                                        }
                                    )
                                )
                            }                        
                        }
                    
                        $('#id_key_min_value').attr('value', min_value)
                        $('#id_key_max_value').attr('value', max_value)
                        $('#id_key_units').html(display_units)
                        
                        /*
                        var scale_divisions = range/range_mag
                        alert(""+range+" "+range_mag+" "+scale_divisions)
                        
                        var scale_html = '';
                        for (
                            var i = 0;
                            i < scale_divisions-1;
                            i++
                        ) {
                            scale_html += '<td style="border-left:1px solid black">&nbsp;</td>'
                        }
                        $('#id_key_scale_tr').html(
                            scale_html+'<td style="border-left:1px solid black;border-right:1px solid black;">&nbsp;</td>'
                        )
                        */
                    //}
                    
                    plugin.overlay_layer.addFeatures(features)
                    plugin.last_query_expression = query_expression
                    done()
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                window.jqXHR = jqXHR
                var responseText = jqXHR.responseText
                var error_message = responseText.substr(0, responseText.indexOf('<!--'))
                var error = $.parseJSON(error_message)
                if (error.error == 'SyntaxError') {
                    var query_expression_lines = query_expression.split('\n')
                    var indent = "#"
                    for (var i=0; i<error.offset-1; i++) {
                        indent+=" "
                    }
                    query_expression_lines.splice(error.lineno, 0, indent+"^ "+error.error)
                    $('textarea#freeform_query_textarea').val(query_expression_lines.join('\n'))
                }
                else {
                    if (error.error == 'MeaninglessUnits') {
                        $('textarea#freeform_query_textarea').val(
                            error.analysis
                        )
                    }
                    else {
                        plugin.set_status(
                            '<a target= "_blank" href="'+
                                plugin.overlay_data_URL+'?'+
                                $.param(query_expression)+
                            '">Error</a>'
                        )
                    }
                }
            },
            complete: function (jqXHR, status) {
                if (status != 'success' && status != 'error') {
                    plugin.set_status(status)
                }
            }
        });
    }
    function SpecPanel(
        panel_id, panel_title, collapsed
    ) {
        function make_combo_box(
            data,
            fieldLabel,
            hiddenName,
            combo_box_size
        ) {
            var options = []
            each(
                data,
                function (option) {
                    options.push([option, option])
                }
            )
            var combo_box = new Ext.form.ComboBox({
                fieldLabel: fieldLabel,
                hiddenName: hiddenName,
                store: new Ext.data.SimpleStore({
                    fields: ['name', 'option'],
                    data: options
                }),
                displayField: 'name',
                typeAhead: true,
                mode: 'local',
                triggerAction: 'all',
                emptyText:'',
                selectOnFocus: true,
                forceSelection: true
            })
            combo_box.setSize(combo_box_size)
            if (!!options[0]) {
                combo_box.setValue(options[0][0])
            }
            return combo_box
        }

        var data_type_combo_box = make_combo_box(
            plugin.data_type_option_names,
            'Data type',
            'data_type',
            {
                width: 115,
                heigth: 25
            }
        )

        var variable_combo_box = make_combo_box(
            plugin.parameter_names,
            'Variable',
            'parameter',
            {
                width: 115,
                heigth: 25
            }
        )
        
        var statistic_combo_box = make_combo_box(
            plugin.aggregation_names,
            'Aggregation',
            'statistic',
            {
                width: 115,
                heigth: 25
            }
        )
        
        function inclusive_range(start, end) {
            var values = []
            for (
                var i = start;
                i <= end;
                i++
            ) {
                values.push(i)
            }
            return values
        }
        var years = inclusive_range(plugin.year_min, plugin.year_max)
        
        var from_year_combo_box = make_combo_box(
            years,
            null,
            'from_year',
            {width:60, height:25}
        )
        from_year_combo_box.setValue(plugin.year_min)
        
        var from_month_combo_box = make_combo_box(
            months,
            null,
            'from_month',
            {width:50, height:25}
        )
        var to_year_combo_box = make_combo_box(
            years,
            null,
            'to_year',
            {width:60, height:25}
        )
        to_year_combo_box.setValue(2011)
        var to_month_combo_box = make_combo_box(
            months,
            null,
            'to_month',
            {width:50, height:25}
        )
        
        var month_filter = []
        // if none are picked, don't do annual aggregation
        // if some are picked, aggregate those months
        // if all are picked, aggregate for whole year
        each('DNOSAJJMAMFJ',
            function (
                month_letter,
                month_index
            ) {
                month_filter.unshift(
                    { html:month_letter, border: false }
                )
                month_filter.push(
                    new Ext.form.Checkbox({
                        name: 'month-'+month_index,
                        checked: false
                    })
                )
            }
        )
        var annual_aggregation_check_box = new Ext.form.Checkbox({
            name: 'annual_aggregation',
            checked: true,
            fieldLabel: 'Annual aggregation'
        })
        var month_checkboxes_id = panel_id+'_month_checkboxes'
        annual_aggregation_check_box.on('check', function(a, value) {
            var month_checkboxes = $('#'+month_checkboxes_id)
            if (value) {
                month_checkboxes.show(300)
            }
            else {
                month_checkboxes.hide(300)
            }
        })

        return new Ext.FormPanel({
            id: panel_id,
            title: panel_title,
            collapsible: true,
            collapseMode: 'mini',
            collapsed: collapsed,
            items: [{
                region: 'center',
                items: [
                    new Ext.form.FieldSet({
                        style: 'margin: 0px; border: none;',
                        items: [
                            //data_type_combo_box,
                            variable_combo_box,
                            statistic_combo_box,
                            annual_aggregation_check_box,
                            // month filter checkboxes
                            {
                                id: month_checkboxes_id,
                                border: false,
                                layout: {
                                    type: 'table',
                                    columns: 12,
                                },
                                defaults: {
                                    width: '16px',
                                    height: '1.3em',
                                    style: 'margin: 0.1em;'
                                },
                                items: month_filter
                            },
                            new Ext.form.CompositeField(
                                {
                                    fieldLabel: 'From',
                                    items:[
                                        from_year_combo_box,
                                        from_month_combo_box
                                    ]
                                }
                            ),
                            new Ext.form.CompositeField(
                                {
                                    fieldLabel: 'To',
                                    items:[
                                        to_year_combo_box,
                                        to_month_combo_box
                                    ]
                                }
                            ),
                        ]
                    })
                ]
            }]
        })
    }
    
    function form_query_expression(ext_form) {
        form_values = ext_form.getValues()
        var month_names = []
        each(
            [0,1,2,3,4,5,6,7,8,9,10,11],
            function (
                month_number
            ) {
                if (
                    form_values['month-'+month_number] == 'on'
                ) {
                    month_names.push(
                        months[month_number+1]
                    )
                }
            }
        )
        return (
            form_values.statistic+'(\n'+
                '    "'+
                form_values.parameter.replace(new RegExp('\\+','g'),' ')+'",\n'+
                '    FromDate('+form_values.from_year +
                    (form_values.from_month?', '+form_values.from_month:'')+
                    '),\n'+
                '    ToDate('+form_values.to_year +
                    (form_values.to_month?', '+form_values.to_month:'')+'),\n'+
                '    Months('+month_names.join(',')+')\n'+
            ')'
        )
    }

    plugin.addToMapWindow = function (items) {
        // create the panels
        var climate_data_panel = SpecPanel(
            'climate_data_panel',
            'Select data:',
            false
        )
        // This button does the simplest "show me data" overlay
        plugin.update_map_layer_from_form = function () {
            plugin.update_map_layer(
                form_query_expression(climate_data_panel.getForm())
            )
        }
        var update_map_layer_button = new Ext.Button({
            text: 'Show on map',
            disabled: false,
            handler: plugin.update_map_layer_from_form
        });
        climate_data_panel.addButton(update_map_layer_button)
        items.push(climate_data_panel)
        
        var comparison_panel = SpecPanel(
            'comparison_panel',
            'Compare with... (subtract from)',
            true
        )
        // This button does the comparison overlay
        plugin.update_map_layer_from_comparison = function () {
            plugin.update_map_layer(
                
                form_query_expression(comparison_panel.getForm()) + ' - ' +
                form_query_expression(climate_data_panel.getForm())
            )
        }
        var update_map_layer_comparison_button = new Ext.Button({
            text: 'Compare and show on map',
            disabled: false,
            handler: plugin.update_map_layer_from_comparison
        });
        comparison_panel.addButton(update_map_layer_comparison_button)
        items.push(comparison_panel)
        
        var show_chart_button = new Ext.Button({
            text: 'Show chart for selected places',
            disabled: true,
            handler: function() {
                // create URL
                var place_ids = []
                var place_names = []
                each(
                    plugin.overlay_layer.selectedFeatures, 
                    function (feature) {
                        var place_id = feature.attributes.place_id
                        place_ids.push(place_id)
                        var place = plugin.places[place_id]
                        place_names.push(
                            (place && (!!place.name)? place.name: place_id)
                        )
                    }
                )
                plugin.last_query_expression
                var query_expression = plugin.last_query_expression
                var spec = JSON.stringify({
                    place_ids: place_ids,
                    query_expression: query_expression
                })
                
                var chart_name = [
                    query_expression,
                    'for', (
                        place_ids.length < 4?
                        ': '+ place_names.join(', '):
                        place_ids.length+' places'
                    )
                ].join(' ')

                // get hold of a chart manager instance
                if (!plugin.chart_window) {
                    var chart_window = plugin.chart_window = window.open(
                        plugin.chart_popup_URL,
                        'chart', 
                        'width=660,height=600,toolbar=0,resizable=0'
                    )
                    chart_window.onload = function () {
                        chart_window.chart_manager = new chart_window.ChartManager(plugin.chart_URL)
                        chart_window.chart_manager.addChartSpec(spec, chart_name)
                    }
                    chart_window.onbeforeunload = function () {
                        delete plugin.chart_window
                    }
                } else {
                    // some duplication here:
                    plugin.chart_window.chart_manager.addChartSpec(spec, chart_name)
                }
            }
        })
        plugin.show_chart_button = show_chart_button
 
        // copied and pasted from the charting button
        var buy_data_button = new Ext.Button({
            text: 'Buy data',
            disabled: false,
            handler: function() {
                // create URL
                var place_ids = []
                var place_names = []
                each(
                    plugin.overlay_layer.selectedFeatures, 
                    function (feature) {
                        var place_id = feature.attributes.place_id
                        place_ids.push(place_id)
                        var place = plugin.places[place_id]
                        place_names.push(
                            (place && (!!place.name)? place.name: place_id)
                        )
                    }
                )
                plugin.last_query_expression
                var query_expression = plugin.last_query_expression
                var spec = JSON.stringify({
                    place_ids: place_ids,
                    query_expression: query_expression
                })
                var data_name = [
                    query_expression,
                    'for', (
                        place_ids.length < 4?
                        ': '+ place_names.join(', '):
                        place_ids.length+' places'
                    )
                ].join(' ')

                // get hold of a data manager instance
                if (!plugin.buy_data_window) {
                    var buy_data_window = plugin.buy_data_window = window.open(
                        plugin.buy_data_popup_URL,
                        'buy_data', 
                        'width=600,height=400,toolbar=0,resizable=0'
                    )
                    buy_data_window.onload = function () {
                        buy_data_window.data_manager = new buy_data_window.DataPurchaseManager(plugin.data_URL)
                        buy_data_window.data_manager.addDataPurchaseSpec(spec, data_name)
                    }
                    buy_data_window.onbeforeunload = function () {
                        delete plugin.buy_data_window
                    }
                } else {
                    // some duplication here:
                    plugin.buy_data_window.data_manager.addDataPurchaseSpec(spec, data_name)
                }
            }
        })
        plugin.buy_data_button = buy_data_button
       
        var freeform_query_panel = new Ext.Panel({
            id: 'freeform_query',
            title: 'Freeform query',
            collapsible: true,
            collapseMode: 'mini',
            collapsed: true,
            items: [
                {
                    html: (
                        '<textarea id="freeform_query_textarea" style="width:100%; height:10em;">'+
                        initial_query_expression+
                        '</textarea>'
                    )
                }
            ]
        })
        // This button does the freeform query overlay
        plugin.update_map_layer_from_freeform_query = function () {
            plugin.update_map_layer(
                $('textarea#freeform_query_textarea').val()
            )
        }
        var freeform_query_button = new Ext.Button({
            text: 'Compute and show on map',
            disabled: false,
            handler: plugin.update_map_layer_from_freeform_query
        });
        freeform_query_panel.addButton(freeform_query_button)
        
        items.push(freeform_query_panel)
        
        var key_panel = new Ext.Panel({
            id: 'key_panel',
            title: 'Key',
            collapsible: false,
            collapseMode: 'mini',
            items: [
                {
                    html:'<table width="100%" style="background-image:;"><tr><td style="width:33%; text-align:left;"><input size=5 id="id_key_min_value" value="Min"/></td><td style="text-align:center;"><span id="id_key_units">Units</span></td><td style="width:33%; text-align:right;"><input id="id_key_max_value" size=5 value="Max" style="text-align:right;"/></td></tr></table>'
                },
                {
                    html:'<img id="key_colour_scale" width="100%" height="15px" />'
                },
                new Ext.form.Checkbox({
                    name: 'key-lock',
                    checked: false,
                    boxLabel: 'lock limits between queries',
                    style:'padding:1em;'
                })
            ]
        })
        key_panel.addButton(buy_data_button)
        
        key_panel.addButton(show_chart_button)
        items.push(key_panel)
        
        items.push({
            autoEl: {
                    tag: 'div',
                    id: 'error_div'
                }                
            }
        )
        plugin.set_status = function (html_message) {
            $('#error_div').html(html_message)
        }
    }
}
