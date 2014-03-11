import logging
from flask import render_template
from widgets import ChartWidget, DirectChartWidget, MultipleChartWidget
from ..widgets import SearchWidget
from ..security.decorators import has_access
from ..baseviews import BaseModelView, expose
from ..urltools import *

log = logging.getLogger(__name__)


class BaseChartView(BaseModelView):
    """
        This is the base class for all chart views. 
        Use ChartView or TimeChartView, override their properties and these
        to customise your charts
    """

    chart_template = 'appbuilder/general/charts/chart.html'
    """ The chart template, override to implement your own """
    chart_widget = ChartWidget
    """ Chart widget override to implement your own """
    search_widget = SearchWidget
    """ Search widget override to implement your own """

    chart_title = 'Chart'
    """ A title to be displayed on the chart """
    default_view = 'chart'

    chart_type = 'PieChart'
    """ The chart type PieChart, ColumnChart, LineChart """
    chart_3d = 'true'
    """ Will display in 3D? """
    width = 400
    """ The width """
    height = '400px'

    group_bys = {}
    """ New for 0.6.4, on test, don't use yet """


    def _get_chart_widget(self, value_columns=None, widgets=None, **args):
        widgets = widgets or dict()
        widgets['chart'] = self.chart_widget(route_base=self.route_base,
                                             chart_title=self.chart_title,
                                             chart_type=self.chart_type,
                                             chart_3d=self.chart_3d,
                                             value_columns=value_columns, **args)
        return widgets


class BaseSimpleGroupByChartView(BaseChartView):
    group_by_columns = []
    """ A list of columns to be possibly grouped by, this list must be filled """

    def __init__(self, **kwargs):
        if not self.group_by_columns:
            raise Exception('Base Chart View property <group_by_columns> must not be empty')
        else: super(BaseChartView, self).__init__(**kwargs)


class BaseSimpleDirectChartView(BaseChartView):
    direct_columns = []
    """
        Make chart using the column on the list
        chart_columns = [('X column','Y1 Column','Y2 Column, ...),('X Column','Y1 Column',...),...]
    """
    def __init__(self, **kwargs):
        if not self.direct_columns:
            raise Exception('Base Chart View property <direct_columns> must not be empty')
        else: super(BaseChartView, self).__init__(**kwargs)


    def get_group_by_columns(self):
        """
            returns first item (X Column) from direct_columns
            Used in template, so that user can choose from options
        """
        return [item[0] for item in self.direct_columns]

class ChartView(BaseSimpleGroupByChartView):
    """
        Provides a simple (and hopefully nice) way to draw charts on your application.

        This will show Google Charts based on group by of your tables.                
    """

    @expose('/chart/<group_by>')
    @expose('/chart/')
    @has_access
    def chart(self, group_by=''):
        form = self.search_form.refresh()
        get_filter_args(self._filters)

        group_by = group_by or self.group_by_columns[0]
        value_columns = self.datamodel.query_simple_group(group_by, filters=self._filters)

        widgets = self._get_chart_widget(value_columns=value_columns)
        widgets = self._get_search_widget(form=form, widgets=widgets)
        return render_template(self.chart_template, route_base=self.route_base,
                               title=self.chart_title,
                               label_columns=self.label_columns,
                               group_by_columns=self.group_by_columns,
                               height=self.height,
                               widgets=widgets,
                               baseapp=self.baseapp)


class TimeChartView(BaseSimpleGroupByChartView):
    """
        Provides a simple way to draw some time charts on your application.

        This will show Google Charts based on count and group by month and year for your tables.
    """

    chart_template = 'appbuilder/general/charts/chart_time.html'
    chart_type = 'ColumnChart'

    @expose('/chart/<group_by>/<period>')
    @expose('/chart/')
    @has_access
    def chart(self, group_by='', period=''):
        form = self.search_form.refresh()
        get_filter_args(self._filters)

        group_by = group_by or self.group_by_columns[0]

        if period == 'month' or not period:
            value_columns = self.datamodel.query_month_group(group_by, filters=self._filters)
        elif period == 'year':
            value_columns = self.datamodel.query_year_group(group_by, filters=self._filters)
        widgets = self._get_chart_widget(value_columns=value_columns)
        widgets = self._get_search_widget(form=form, widgets=widgets)
        return render_template(self.chart_template, route_base=self.route_base,
                               title=self.chart_title,
                               label_columns=self.label_columns,
                               group_by_columns=self.group_by_columns,
                               height=self.height,
                               widgets=widgets,
                               baseapp=self.baseapp)


class DirectChartView(BaseSimpleDirectChartView):
    """
        This class is responsible for displaying a chart with
        direct model values. No group by is processed.
    """
    chart_type = 'ColumnChart'

    chart_widget = DirectChartWidget

    def _dict_to_json(self, xcol, ycols, labels, value_columns):
        json_data = dict()
        json_data['cols'] = [{'id': xcol,
                             'label': labels[xcol],
                              'type': 'string'}]
        for ycol in ycols:
            print "YCOL {0}".format(ycol)
            json_data['cols'].append({'id': ycol,
                                      'label': labels[ycol],
                                      'type': 'number'})
        json_data['rows'] = []
        for value in value_columns:
            row = {'c': []}
            for ycol in ycols:
                row['c'].append({'v': (value[xcol]).encode('utf-8')})
                if value[ycol]:
                    row['c'].append({'v': int(value[ycol])})
                else:
                    row['c'].append({'v': 0})
            json_data['rows'].append(row)
        return json_data

    @expose('/chart/<direct>')
    @expose('/chart/')
    @has_access
    def chart(self, direct=''):
        form = self.search_form.refresh()
        get_filter_args(self._filters)

        direct = direct or self.direct_columns[0]
        count, lst = self.datamodel.query(filters=self._filters)
        value_columns = self.datamodel.get_values(lst, list(direct))
        log.info("VALUES {0}".format(value_columns))
        print "DIR {0}".format(direct)
        log.info("JSON VAL {0}".format(self._dict_to_json(direct[0], direct[1:], self.label_columns, value_columns)))

        value_columns = self._dict_to_json(direct[0], direct[1:], self.label_columns, value_columns)
        widgets = self._get_chart_widget(value_columns=value_columns)
        widgets = self._get_search_widget(form=form, widgets=widgets)
        return render_template(self.chart_template, route_base=self.route_base,
                               title=self.chart_title,
                               label_columns=self.label_columns,
                               group_by_columns=self.get_group_by_columns(),
                               height=self.height,
                               widgets=widgets,
                               baseapp=self.baseapp)


class MultipleChartView(BaseChartView):
    chart_template = 'appbuilder/general/charts/chart.html'
    chart_type = 'ColumnChart'

    chart_widget = MultipleChartWidget

    @expose('/chart/')
    @has_access
    def chart(self):
        form = self.search_form.refresh()
        get_filter_args(self._filters)

        value_columns = self.datamodel.query_group(self.group_bys[0], filters=self._filters)

        widgets = self._get_chart_widget(value_columns=value_columns)
        widgets = self._get_search_widget(form=form, widgets=widgets)
        return render_template(self.chart_template, route_base=self.route_base,
                               title=self.chart_title,
                               label_columns=self.label_columns,
                               group_by_columns=self.group_by_columns,
                               height=self.height,
                               widgets=widgets,
                               baseapp=self.baseapp)
