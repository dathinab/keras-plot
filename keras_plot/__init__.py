"""
a mostly stright forward port of blocks_extras.extensions.Plot to Keras
it has all(/most of) the bad points of it's original, like the requirement for bokeh==0.10 (instead of >=0.11).

there is one change wrt. to the default server_url and some simple refactoring
where the implementation was unnecessarily complex
"""

from collections import namedtuple
from functools import total_ordering
import logging
import signal
import time
from six.moves.queue import PriorityQueue
from subprocess import Popen, PIPE
from threading import Thread
from bokeh.document import Document
from bokeh.plotting import figure
from bokeh.session import Session
from keras.callbacks import Callback


logger = logging.getLogger(__name__)

DEFAULT_SRV_URL = "http://localhost:5006"

class PlottingExtension(Callback):
    """Base class for extensions doing Bokeh plotting.

    Parameters
    ----------
    document_name : str
        The name of the Bokeh document. Use a different name for each
        experiment if you are storing your plots.

    ##start_server : Removed, as it has a number of problems inkl. zombi bokeh processes!

    server_url : str, optional
        Url of the bokeh-server. Ex: when starting the bokeh-server with
        ``bokeh-server --ip 0.0.0.0`` at ``alice``, server_url should be
        ``http://alice:5006``. Defaults to http://localhost:5006.
    clear_document : bool, optional
        Whether or not to clear the contents of the server-side document
        upon creation. If `False`, previously existing plots within the
        document will be kept. Defaults to `True`.

    """
    def __init__(self, document_name, server_url=None,
                 clear_document=True):
        super(PlottingExtension, self).__init__()
        self.document_name = document_name
        self.server_url = DEFAULT_SRV_URL if server_url is None else server_url
        self.session = Session(root_url=self.server_url)
        self.document = Document()
        self._setup_document(clear_document)

    def _setup_document(self, clear_document=False):
        self.session.use_doc(self.document_name)
        self.session.load_document(self.document)
        if clear_document:
            self.document.clear()
        self._document_setup_done = True

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop('_sub', None)
        state.pop('session', None)
        state.pop('_push_thread', None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.session = Session(root_url=self.server_url)
        self._document_setup_done = False

    def on_callback(self, logs={}):
        if not self._document_setup_done:
            self._setup_document()

    @property
    def push_thread(self):
        if not hasattr(self, '_push_thread'):
            self._push_thread = PushThread(self.session, self.document)
            self._push_thread.start()
        return self._push_thread

    def store_data(self, obj):
        self.push_thread.put(obj, PushThread.PUT)

    def push_document(self, after_training=False):
        self.push_thread.put(after_training, PushThread.PUSH)



class Plot(PlottingExtension):
    r"""Live plotting of monitoring channels.

    In most cases it is preferable to start the Bokeh plotting server
    manually, so that your plots are stored permanently.


    Parameters
    ----------
    document_name : str
        See :class:`PlottingExtension` for details.
    channels : list of channel specifications
        A channel specification is either a list of channel names, or a
        dict with at least the entry ``channels`` mapping to a list of
        channel names. The channels in a channel specification will be
        plotted together in a single figure, so use e.g. ``[['test_cost',
        'train_cost'], ['weight_norms']]`` to plot a single figure with the
        training and test cost, and a second figure for the weight norms.

        EDIT: instead of string the metrics can be specified by passing the same functions you pass to metrics
         (as long as there is only one ouput in the model)

        When the channel specification is a list, a bokeh figure will
        be created with default arguments. When the channel specification
        is a dict, the field channels is used to specify the contnts of the
        figure, and all remaining keys are passed as ``\*\*kwargs`` to
        the ``figure`` function.

    """
    # Tableau 10 colors
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

    @staticmethod
    def get_metric_name(metric):
        """get the name for a gicen metric,

        if metric is a string this works like the identity function,
        excepts, that "accuaracy" becomes "acc".

        This function does not work if there are multiple outputs
        and the parameter is not a string
        """
        if metric == 'accuracy':
            return 'acc'
        if hasattr(metric, '__name__'):
            if metric.__module__ == 'keras.objectives':
                raise ValueError("please use keras.metrics.* for metrics (in model.compile!)" +
                                 "using keras.objectives.* can lead to strange errors")
            # e.g. functions, or Functors with __name__ set
            return metric.__name__
        return str(metric)

    def __init__(self, document_name, channels, after_every_batch=False,
                 clear_document=True, server_url=None):
        super(Plot, self).__init__(document_name, server_url=server_url)
        self.after_every_batch = after_every_batch
        self._iteration = 0

        self.data_sources = {}
        # Create figures for each group of channels
        self.metric2figure = {}
        self.metric2color = {}
        for i, list_of_plots in enumerate(channels):
            channel_set_opts = {}
            if isinstance(list_of_plots, dict):
                channel_set_opts = list_of_plots
                list_of_plots = channel_set_opts.pop('channels')

            channel_set_opts.setdefault('title',
                                        '{} #{}'.format(document_name, i + 1))
            channel_set_opts.setdefault('x_axis_label', 'iterations')
            channel_set_opts.setdefault('y_axis_label', 'value')
            current_figure = figure(**channel_set_opts)

            for j, metric in enumerate(list_of_plots):
                metric_name = self.get_metric_name(metric)
                self.metric2figure[metric_name] = current_figure
                self.metric2color[metric_name] = self.colors[j % len(self.colors)]

    def on_train_begin(self, logs={}):
        self.on_callback(logs)

    def on_train_end(self, logs={}):
        self.on_callback(logs, after_training=True)

    def on_batch_end(self, batch, logs={}):
        if self.after_every_batch:
            self._iteration = batch
            self.on_callback(logs)

    def on_epoch_end(self, epoch, logs={}):
        if not self.after_every_batch:
            self._iteration = epoch
        self.on_callback(logs)

    def on_callback(self, logs, after_training=False):
        super(Plot, self).on_callback(logs)

        for metric in self.params['metrics']:
            # logs does not always contain all metrics in keras
            # TODO error[log] if len(logs) > 0 and metric not in logs
            if metric in self.metric2figure and metric in logs:
                value = logs[metric]
                if metric not in self.data_sources:
                    line_color = self.metric2color[metric]
                    fig = self.metric2figure[metric]
                    fig.line([self._iteration], [value],
                             legend=metric, name=metric,
                             line_color=line_color)
                    self.document.add(fig)
                    renderer = fig.select({ 'name': metric })
                    self.data_sources[metric] = renderer[0].data_source
                else:
                    self.data_sources[metric].data['x'].append(self._iteration)
                    self.data_sources[metric].data['y'].append(value)
                    self.store_data(self.data_sources[metric])
        self.push_document(after_training)


@total_ordering
class _WorkItem(namedtuple('BaseWorkItem', ['priority', 'obj'])):
    __slots__ = ()

    def __lt__(self, other):
        return self.priority < other.priority


class PushThread(Thread):
    PUSH, PUT = range(2)

    def __init__(self, session, document):
        self.session = session
        self.document = document
        super(PushThread, self).__init__()
        self.queue = PriorityQueue()
        self.setDaemon(True)

    def put(self, obj, priority):
        self.queue.put(_WorkItem(priority, obj))

    def run(self):
        while True:
            # does it even make sense to have a priority que?
            # (instead of a simple FIFO, I mean we have a single-producer single-consumer
            #  scenario)
            priority, obj = self.queue.get()
            if priority == PushThread.PUT:
                self.session.store_objects(obj)
            elif priority == PushThread.PUSH:
                self.session.store_document(self.document)
                # delete queued objects when training has finished
                if obj == 'after_training':
                    with self.queue.mutex:
                        del self.queue.queue[:]
                    break
            self.queue.task_done()
