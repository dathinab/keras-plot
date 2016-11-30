
# keras-plot

A mostly strait forward port of `blocks-extras.extensions.Plot` to a keras callback,
including most of the original drawback and benefits.

Note: Require bokeh version 0.10!!, like the blocks version

Note: this is mostly a fast straight forward port, with some little goodies added in and a bit of refactoring
  do not expect production quality or maintance for this package


## Installation

No special inatallation requirements, but because it relies on a old version of bokeh I won't upload it
on PyPI, you can use e.g.: `pip install git+https://github.com/dathinab/keras-plot.git --user`


## Changes compared to `blocks-extras.extensions.Plot`

- some refactoring making unessesary complex internal code mor simple and readable
- removed `start_server` option, as it should not have existed at all
- changed the default `server_url `behaviour (there is not simple mapping from the config mechanism from blocks to keras)
- added some small nice goodies:
    - you can just pass in the same functions to the plots channel parameter, as you can pass to the fit
      functions `metrics` parameter. Be aware that many functions are implemented both in `keras.objectives` and
      `keras.metrics` and that e.g. a `mean_squared_error` objective is not the same as a `mean_squared_error` metric!
      The Plot class intentionally rejects keras.objective functions as this is mostly likely a bug, which can lead
      to non obvious error messages, if the objective is also used as a metric in the training functionality.

    - Also both 'accuracy' and 'acc' will map to 'acc' as this is how keras behaves.


## Example

(note: it's quite a nonsensical example)

Before running this example make sure to start a bokeh server of version 0.10 on the
localhost, port 5006 (wich is the default for it) or add parameters to Plot constructor.

```python
from keras_plot import Plot
import numpy

from keras.models import Sequential
from keras.layers import Dense, Activation

model = Sequential()
model.add(Dense(output_dim=1, input_dim=100))
model.add(Activation("relu"))

from keras.optimizers import SGD
import keras.objectives as objectives
from keras.metrics import mean_absolute_error, binary_accuracy

model.compile(
    loss=objectives.mean_squared_error,
    optimizer=SGD(),
    metrics=[binary_accuracy, mean_absolute_error]
)

X_train = numpy.random.random(size=(300, 100))
Y_train = numpy.random.randint(0, 2, size=(300, 1))

model.fit(X_train, Y_train, nb_epoch=50, batch_size=10, callbacks=[
    Plot(
        document_name="test4231",
        channels=[
            # the first plot (not that MSE+Accuracy in same plot make hardly any sense)
            ['loss', binary_accuracy],
            # the second plot
            [mean_absolute_error]
        ],
    )
])
```


## Collection of possible improvements

- switch to newer bokeh version
- when plotting after every batch also add a (samely) colored graph ploted after every epoch, which is kind of
  the smothed version of "after every batch"
- possible mix "after every batch" and "after every epoch" for different metrics
- possible add filters like "moving window smoothing"
- change API to accept bokeh Session instead of a url
    - for login, configuarability etc.
    - possible add some load/create from config function for it
